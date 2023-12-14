import base64
import json
import logging
import sys
from logging import StreamHandler, FileHandler
from dataclasses import dataclass, field
from datetime import datetime
from typing import Tuple
from argparse import ArgumentParser

import kubernetes.client
import jwt
import requests
from gitlab import Gitlab
from gitlab.exceptions import GitlabAuthenticationError
from kubernetes import config
from kubernetes.client.exceptions import ApiException

configuration = config.load_kube_config()
now = datetime.utcnow()
log_file = f"patching-sessions-log-{now.isoformat()}.txt"
logging.basicConfig(level=logging.INFO, handlers=[StreamHandler(sys.stdout), FileHandler(log_file)])


@dataclass
class Tokens:
    client_id: str
    renku_url: str
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    client_secret: str = field(repr=False)

    def __post_init__(self):
        self.renku_url = self.renku_url.rstrip("/")


def gitlab_token_is_valid(token: str, gitlab_url: str) -> bool:
    gl = Gitlab(url=gitlab_url, oauth_token=token)
    try:
        gl.auth()
    except GitlabAuthenticationError:
        logging.info("The gitlab token is not valid - will be refreshed")
        return False
    return True


def patch_image_pull_secret(
    statefulset_name: str, namespace: str, new_token: str, dry_run: bool = True
):
    with kubernetes.client.ApiClient(configuration) as api_client:
        secret_name = f"{statefulset_name}-image-secret"
        core_instance = kubernetes.client.CoreV1Api(api_client)
        try:
            secret = core_instance.read_namespaced_secret(secret_name, namespace)
        except ApiException as err:
            if err.status == 404:
                logging.info(
                    f"The statefulset {statefulset_name} does not have an image pull secret"
                )
                return
        old_docker_config = json.loads(base64.b64decode(secret.data[".dockerconfigjson"]).decode())
        hostname = list(old_docker_config["auths"].keys())[0]
        new_docker_config = {
            "auths": {
                hostname: {
                    "Username": "oauth2",
                    "Password": new_token,
                    "Email": old_docker_config["auths"][hostname]["Email"],
                }
            }
        }
        patch_path = "/data/.dockerconfigjson"
        patch = [
            {
                "op": "replace",
                "path": patch_path,
                "value": base64.b64encode(json.dumps(new_docker_config).encode()).decode(),
            }
        ]
        logging.info(f"Preparing to patch secret {secret_name} at {patch_path}")
        if not dry_run:
            core_instance.patch_namespaced_secret(
                secret_name,
                namespace,
                patch,
            )
            logging.info(
                f"Patch on image pull secret {secret_name} for {statefulset_name} complete"
            )
        else:
            logging.info("Skipped patch on secret because this is a dry run, nothing changed")


def get_new_token(tokens: Tokens, gitlab_url: str) -> Tuple[str, int] | None:
    renku_access_token = tokens.access_token
    renku_access_token_parsed = jwt.decode(renku_access_token, options={"verify_signature": False})
    exp = datetime.fromtimestamp(renku_access_token_parsed["exp"])
    if exp < datetime.utcnow():
        logging.info("The renku access token is not valid and needs to be refreshed...")
        kc_token_url = f"{tokens.renku_url}/auth/realms/Renku/protocol/openid-connect/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": tokens.refresh_token,
            "client_id": tokens.client_id,
            "client_secret": tokens.client_secret,
        }
        res = requests.post(kc_token_url, data=payload)
        if res.status_code != 200:
            logging.warning(
                "Could not refresh renku access token, "
                f"status code {res.status_code}, response {res.text}"
            )
            return None
        logging.info("Successfully refreshed renku access token")
        renku_access_token = res.json()["access_token"]
    gateway_url = f"{tokens.renku_url}/api/auth/gitlab/exchange"
    res = requests.get(gateway_url, headers={"Authorization": f"bearer {renku_access_token}"})
    if res.status_code != 200:
        logging.info(
            "Could not refresh gitlab access token at the Gateway, "
            f"status code {res.status_code}, {res.text}"
        )
        return None
    new_token = res.json()["access_token"]
    new_token_expires_at = res.json()["expires_at"]
    if not gitlab_token_is_valid(new_token, gitlab_url):
        logging.error("Retrieved a new gitlab token from the gateway but it is not valid")
        return None
    logging.info("Successfully refreshed gitlab access token")
    return (new_token, -1 if not new_token_expires_at else new_token_expires_at)


def find_env_var(container, env_name: str) -> Tuple[int, str] | None:
    if container is None:
        return None
    env_var = next(
        filter(
            lambda x: x[1].name == env_name,
            enumerate(container.env),
        ),
        None,
    )
    if not env_var:
        return None
    ind = env_var[0]
    val = env_var[1].value
    return (ind, val)


def extract_tokens(name: str, namespace: str) -> Tokens | None:
    with kubernetes.client.ApiClient(configuration) as api_client:
        api_instance = kubernetes.client.AppsV1Api(api_client)
        ss = api_instance.read_namespaced_stateful_set(name, namespace)
        if len(ss.spec.template.spec.containers) < 3:
            logging.warning(f"Statefulset {name} has fewer than 3 containers, skipping")
            return None
        git_proxy_container_index = 2
        git_proxy_container = ss.spec.template.spec.containers[git_proxy_container_index]
        access_token = find_env_var(git_proxy_container, "RENKU_ACCESS_TOKEN")
        refresh_token = find_env_var(git_proxy_container, "RENKU_REFRESH_TOKEN")
        renku_url = find_env_var(git_proxy_container, "RENKU_URL")
        client_id = find_env_var(git_proxy_container, "RENKU_CLIENT_ID")
        client_secret = find_env_var(git_proxy_container, "RENKU_CLIENT_SECRET")
        if access_token is None:
            logging.warning(f"Could not find access token in {name}")
            return None
        if refresh_token is None:
            logging.warning(f"Could not find refresh token in {name}")
            return None
        if renku_url is None:
            logging.warning(f"Could not find renku URL in {name}")
            return None
        if client_id is None:
            logging.warning(f"Could not find client id in {name}")
            return None
        if client_secret is None:
            logging.warning(f"Could not find client secret in {name}")
            return None
        return Tokens(
            client_id[1], renku_url[1], access_token[1], refresh_token[1], client_secret[1]
        )


def patch_session(
    name: str, namespace: str, gitlab_url: str, dry_run: bool = True, only_hibernated: bool = True
):
    logging.info(f"Starting checks and potential patching on session {name}")
    with kubernetes.client.ApiClient(configuration) as api_client:
        api_instance = kubernetes.client.AppsV1Api(api_client)
        try:
            ss = api_instance.read_namespaced_stateful_set(name, namespace)
        except ApiException as err:
            if err.status == 404:
                logging.warning(f"Could not find statefulset {name}, skipping")
                return
        if (ss.spec.replicas != 0 and ss.status.available_replicas != 0) and only_hibernated:
            logging.warning(f"Statefulset {name} is not hibernated or crashing, skipping")
            return
        if len(ss.spec.template.spec.containers) < 3:
            logging.warning(f"Statefulset {name} has fewer than 3 containers, skipping")
            return
        if len(ss.spec.template.spec.init_containers) < 3:
            logging.warning(f"Statefulset {name} has less than 3 containers, skipping")
            return
        git_proxy_container_index = 2
        git_proxy_container = ss.spec.template.spec.containers[git_proxy_container_index]
        git_init_container_index = 2
        git_init_container = ss.spec.template.spec.init_containers[git_init_container_index]
        expires_at_env = find_env_var(git_proxy_container, "GITLAB_OAUTH_TOKEN_EXPIRES_AT")
        gitlab_token_env = find_env_var(git_proxy_container, "GITLAB_OAUTH_TOKEN")
        if expires_at_env is None:
            logging.warning(
                f"Could not locate gitlab access token expiry env var in {name}, skipping"
            )
            return
        if gitlab_token_env is None:
            logging.warning(f"Could not locate gitlab token env in {name}, skipping")
            return
        if expires_at_env[1] != "-1" and gitlab_token_is_valid(gitlab_token_env[1], gitlab_url):
            logging.warning(f"The gitlab token at {name} is most likely valid, skipping")
            return
        tokens = extract_tokens(name, namespace)
        if tokens is None:
            logging.warning(
                "Could not extract the required tokens to "
                f"refresh and patch gitlab token for {name}"
            )
            return
        logging.info(f"Getting a new gitlab access token from gateway for {name}")
        gitlab_token = get_new_token(tokens, gitlab_url)
        if gitlab_token is None:
            logging.error(f"A new gitlab token for {name} could not be acquired, skipping.")
            return
        git_init_token_env = find_env_var(git_init_container, "GIT_CLONE_USER__OAUTH_TOKEN")
        if git_init_token_env is None:
            logging.warning(
                f"Could not find the gitlab token env variable in the init container in {name}"
            )
        patch = [
            {
                "op": "replace",
                "path": "/metadata/labels/renku_io_expired_token_fix",
                "value": "v1",
            },
            {
                "op": "replace",
                "path": (
                    f"/spec/template/spec/containers/{git_proxy_container_index}"
                    f"/env/{expires_at_env[0]}/value"
                ),
                "value": str(gitlab_token[1]),
            },
            {
                "op": "replace",
                "path": (
                    f"/spec/template/spec/containers/{git_proxy_container_index}"
                    f"/env/{gitlab_token_env[0]}/value"
                ),
                "value": gitlab_token[0],
            },
            {
                "op": "replace",
                "path": (
                    f"/spec/template/spec/initContainers/{git_init_container_index}"
                    f"/env/{git_init_token_env[0]}/value"
                ),
                "value": gitlab_token[0],
            },
        ]
        logging.info(f"Preparing to patch statefulset {name}")
        if not dry_run:
            api_instance.patch_namespaced_stateful_set(
                name,
                namespace,
                patch,
            )
            logging.info(f"Patch on statefulset {name} complete")
        else:
            logging.info("Skipped patch because we are doing a dry run - nothing changed.")
        patch_image_pull_secret(name, namespace, gitlab_token[0], dry_run)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Patching expired gitlab access tokens. "
        "Will patch only hibernated and failing sessions. The session statefulset "
        "and if there is one the session image pull secret is patched."
        "WARNING: The currently active K8s context is used to authenticate.",
    )
    parser.add_argument(
        "-g",
        "--gitlab-url",
        type=str,
        help="The full url to the gitlab deployment - i.e. https://gitlab.renkulab.io",
        required=True,
    )
    parser.add_argument(
        "-n",
        "--namespace",
        type=str,
        default="renku",
        help="The K8s namespace where Renku is deployed",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="With this flag none of the sessions are patched.",
    )
    parser.add_argument(
        "-u",
        "--user",
        type=str,
        default=None,
        help="Filter sessions by Keycloak user ID, if omitted run for all users.",
    )
    args = parser.parse_args()
    logging.info(f"Starting with args {args}")
    with kubernetes.client.ApiClient(configuration) as api_client:
        api_instance = kubernetes.client.AppsV1Api(api_client)
        label_selector = "component=singleuser-server"
        if args.user:
            label_selector += f",renku.io/userId={args.user}"
        ss_list = api_instance.list_namespaced_stateful_set(
            namespace=args.namespace,
            label_selector=label_selector,
        )
        logging.info(f"Found {len(ss_list.items)} total sessions")
        for iss, ss in enumerate(ss_list.items):
            ss_name: str = ss.metadata.name
            logging.info("**************************************************************")
            logging.info(f"Processing statefulset {iss+1}/{len(ss_list.items)} {ss_name}")
            if ss_name.startswith("anon-"):
                logging.info(f"{ss_name} is an anonymous session, skipping.")
                logging.info("**************************************************************\n")
                continue
            patch_session(ss_name, args.namespace, args.gitlab_url, args.dry_run)
            logging.info("**************************************************************\n")
