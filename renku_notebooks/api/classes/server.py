from jupyterhub.services.auth import HubOAuth
import os
import requests
import gitlab
from kubernetes import client
from kubernetes.client.rest import ApiException
from hashlib import md5
import base64
import json
import escapism
from urllib.parse import urlparse
from uuid import uuid4
from flask import make_response, jsonify

from ...util.check_image import parse_image_name, get_docker_token, image_exists
from ...util.kubernetes_ import (
    get_k8s_client,
    secret_exists,
    get_all_user_pods,
    filter_pods_by_annotations,
    format_user_pod_data,
)
from ..auth import get_user_info


class Server:
    """Represents a jupuyterhub session."""

    def __init__(
        self,
        user,
        namespace,
        project,
        branch,
        commit_sha,
        notebook,
        image,
        server_options,
    ):
        self._renku_annotation_prefix = "renku.io/"
        self._get_environment_vars()
        self._auth = HubOAuth(
            api_token=os.environ.get("JUPYTERHUB_API_TOKEN"), cache_max_age=60
        )
        self._user = user
        self._prefix = self._auth.api_url
        self._headers = {self._auth.auth_header_name: f"token {self._auth.api_token}"}
        self._oauth_token = self._get_oauth_token()
        self._gl = gitlab.Gitlab(
            self._git_url, api_version=4, oauth_token=self._oauth_token
        )
        self._k8s_client, self._k8s_namespace = get_k8s_client()
        self.safe_username = escapism.escape(
            self._user.get("name"), escape_char="-"
        ).lower()
        self.namespace = namespace
        self.project = project
        self.branch = branch
        self.commit_sha = commit_sha
        self.notebook = notebook
        self.image = image
        self.server_options = server_options
        self.server_name = self.make_server_name(
            self.namespace, self.project, self.branch, self.commit_sha
        )

    def _get_environment_vars(self):
        if os.environ.get("JUPYTERHUB_API_TOKEN", None) is None:
            raise ValueError(
                "The jupyterhub API token is missing, it must be provided in "
                "an environment variable called JUPYTERHUB_API_TOKEN"
            )
        if os.environ.get("GITLAB_URL", None) is None:
            raise ValueError(
                "The gitlab URL is missing, it must be provided in "
                "an environment variable called GITLAB_URL"
            )
        if os.environ.get("IMAGE_REGISTRY", None) is None:
            raise ValueError(
                "The url to the docker image registry is missing, it must be provided in "
                "an environment variable called IMAGE_REGISTRY"
            )
        self._default_image = os.environ.get(
            "NOTEBOOKS_DEFAULT_IMAGE", "renku/singleuser:latest"
        )
        self._image_registry = os.environ.get("IMAGE_REGISTRY")
        self._jupyterhub_authenticator = os.environ.get(
            "JUPYTERHUB_AUTHENTICATOR", "gitlab"
        )
        self._git_url = os.environ.get("GITLAB_URL")
        self._jupyterhub_path_prefix = os.environ.get(
            "JUPYTERHUB_BASE_URL", "/jupyterhub"
        )
        self._jupyterhub_origin = os.environ.get("JUPYTERHUB_ORIGIN", "")

    def _get_oauth_token(self):
        """Retrieve the user's GitLab token from the oauth metadata."""
        if self._jupyterhub_authenticator != "gitlab":
            return None

        auth_state = get_user_info(self._user).get("auth_state", None)
        return None if not auth_state else auth_state.get("access_token")

    @staticmethod
    def make_server_name(namespace, project, branch, commit_sha):
        """Form a 16-digit hash server ID."""
        server_string = f"{namespace}{project}{branch}{commit_sha}"
        return "{project}-{hash}".format(
            project=project[:54], hash=md5(server_string.encode()).hexdigest()[:8]
        )

    def _namespace_exists(self):
        r = requests.get(
            f"{self._git_url}/api/v4/namespaces",
            params={"search": self.namespace},
            headers={"Authorization": f"Bearer {self._oauth_token}"},
        )
        if r.status_code == 200:
            res = r.json()
            res = list(filter(lambda x: x.get("full_path") == self.namespace, res))
            if len(res) == 1:
                return True
        return False

    def _project_exists(self):
        """Retrieve the GitLab project."""
        try:
            self._gl.projects.get(f"{self.namespace}/{self.project}")
        except Exception:
            return False
        else:
            return True

    def _branch_exists(self):
        # the branch name is not required by the API and therefore
        # passing None to this function will return True
        if self.branch is not None:
            try:
                self._gl.projects.get(f"{self.namespace}/{self.project}").branches.get(
                    self.branch
                )
            except Exception:
                return False
            else:
                return True
        return True

    def _commit_sha_exists(self):
        try:
            self._gl.projects.get(f"{self.namespace}/{self.project}").commits.get(
                self.commit_sha
            )
        except Exception:
            return False
        else:
            return True

    def _get_image(self, image):
        # set the notebook image if not specified in the request
        gl_project = self._gl.projects.get(f"{self.namespace}/{self.project}")
        if image is None:
            parsed_image = {
                "hostname": self._image_registry,
                "image": gl_project.path_with_namespace.lower(),
                "tag": self.commit_sha[:7],
            }
            commit_image = (
                f"{self._image_registry}/{gl_project.path_with_namespace.lower()}"
                f":{self.commit_sha[:7]}"
            )
        else:
            parsed_image = parse_image_name(image)
        # get token
        token, is_image_private = get_docker_token(**parsed_image, user=self._user)
        # check if images exist
        image_exists_result = image_exists(**parsed_image, token=token)
        # assign image
        if image_exists_result and image is None:
            # the image tied to the commit exists
            verified_image = commit_image
        elif not image_exists_result and image is None:
            # the image tied to the commit does not exist, fallback to default image
            verified_image = self._default_image
            is_image_private = False
            print(
                f"Image for the selected commit {self.commit_sha} of {self.project}"
                f" not found, using default image {self._default_image}"
            )
        elif image_exists_result and image is not None:
            # a specific image was requested and it exists
            verified_image = image
        else:
            return None, None
        return verified_image, is_image_private

    def _create_registry_secret(self):
        secret_name = f"{self.safe_username}-registry-{str(uuid4())}"
        git_host = urlparse(self._git_url).netloc
        token = self._get_oauth_token()
        payload = {
            "auths": {
                self._image_registry: {
                    "Username": "oauth2",
                    "Password": token,
                    "Email": self._user.get("email"),
                }
            }
        }

        data = {
            ".dockerconfigjson": base64.b64encode(json.dumps(payload).encode()).decode()
        }

        secret = client.V1Secret(
            api_version="v1",
            data=data,
            kind="Secret",
            metadata={
                "name": secret_name,
                "namespace": self._k8s_namespace,
                "annotations": {
                    self._renku_annotation_prefix + "git-host": git_host,
                    self._renku_annotation_prefix + "namespace": self.namespace,
                },
                "labels": {
                    "component": "singleuser-server",
                    self._renku_annotation_prefix + "username": self.safe_username,
                    self._renku_annotation_prefix + "commit-sha": self.commit_sha,
                    self._renku_annotation_prefix + "projectName": self.project,
                },
            },
            type="kubernetes.io/dockerconfigjson",
        )

        if secret_exists(secret_name, self._k8s_client, self._k8s_namespace):
            self._k8s_client.replace_namespaced_secret(
                secret_name, self._k8s_namespace, secret
            )
        else:
            self._k8s_client.create_namespaced_secret(self._k8s_namespace, body=secret)

        return secret

    def _get_start_payload(self):
        verified_image, is_image_private = self._get_image(self.image)
        if verified_image is None:
            return None
        gl_project = self._gl.projects.get(f"{self.namespace}/{self.project}")
        payload = {
            "namespace": self.namespace,
            "project": self.project,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "project_id": gl_project.id,
            "notebook": self.notebook,
            "image": verified_image,
            "git_clone_image": os.getenv("GIT_CLONE_IMAGE", "renku/git-clone:latest"),
            "git_https_proxy_image": os.getenv(
                "GIT_HTTPS_PROXY_IMAGE", "renku/git-https-proxy:latest"
            ),
            "server_options": self.server_options,
        }

        if self._jupyterhub_authenticator == "gitlab" and is_image_private:
            secret = self._create_registry_secret()
            payload["image_pull_secrets"] = [secret.metadata.name]

        return payload

    def start(self):
        if (
            self._namespace_exists()
            and self._project_exists()
            and self._branch_exists()
            and self._commit_sha_exists()
        ):
            payload = self._get_start_payload()
            if payload is None:
                # a specific image was requested but does not exist
                return make_response(
                    jsonify(
                        {
                            "messages": {
                                "error": f"Cannot find/access image {self.image}."
                            }
                        }
                    ),
                    404,
                )
            res = requests.post(
                f"{self._prefix}/users/{self._user['name']}/servers/{self.server_name}",
                json=payload,
                headers=self._headers,
            )
            return res

        msg = []
        if not self._namespace_exists():
            msg.append(f"the namespace {self.namespace} does not exist")
        if not self._project_exists():
            msg.append(f"the project {self.project} does not exist")
        if not self._branch_exists():
            msg.append(f"the branch {self.branch} does not exist")
        if not self._commit_sha_exists():
            msg.append(f"the commit sha {self.commit_sha} does not exist")
        return make_response(
            jsonify(
                {
                    "messages": {
                        "error": {
                            "parsing": [
                                f"creating server {self.server_name} "
                                f"failed because {', '.join(msg)}"
                            ]
                        }
                    }
                }
            ),
            404,
        )

    def server_exists(self):
        return self.get_user_pod() is not None

    def get_user_pod(self):
        pods = get_all_user_pods(self._user, self._k8s_client, self._k8s_namespace)
        pods = filter_pods_by_annotations(
            pods, {"hub.jupyter.org/servername": self.server_name}
        )
        if len(pods) != 1:
            return None
        return pods[0]

    def delete(self, forced=False):
        """Delete user's server with specific name"""
        pod_name = self.get_user_pod().get("metadata", {}).get("name")
        if forced:
            try:
                self._k8s_client.delete_namespaced_pod(
                    pod_name, self._k8s_namespace, grace_period_seconds=30
                )
                return make_response("", 204)
            except ApiException as e:
                msg = f"Cannot delete server: {pod_name} for user: {self._user['name']}, error: {e}"
                print(msg)
                return make_response(
                    jsonify({"messages": {"error": "Cannot force delete server"}}), 400
                )
        else:
            r = requests.delete(
                f"{self._prefix}/users/{self._user['name']}/servers/{self.server_name}",
                headers=self._headers,
            )
            if r.status_code == 204:
                return make_response("", 204)
            elif r.status_code == 202:
                return make_response(
                    jsonify(
                        {
                            "messages": {
                                "information": "The server was not stopped, "
                                "it is taking a while to stop."
                            }
                        }
                    ),
                    r.status_code,
                )
            else:
                message = r.json().get(
                    "message", "Something went wrong while tring to stop the server"
                )
                return make_response(
                    jsonify({"messages": {"error": message}}), r.status_code
                )

    def logs(self, max_log_lines=0, container_name="notebook"):
        pod = self.get_user_pod()
        if pod is None:
            return None
        pod_name = pod.get("metadata", {}).get("name")
        if max_log_lines == 0:
            logs = self._k8s_client.read_namespaced_pod_log(
                pod_name, self._k8s_namespace, container=container_name
            )
        else:
            logs = self._k8s_client.read_namespaced_pod_log(
                pod_name,
                self._k8s_namespace,
                tail_lines=max_log_lines,
                container=container_name,
            )
        return logs

    def k8s_summary(self):
        pod = self.get_user_pod()
        if pod is not None:
            return format_user_pod_data(
                pod,
                self._jupyterhub_path_prefix,
                self._default_image,
                self._renku_annotation_prefix,
                self._jupyterhub_origin,
            )

    @classmethod
    def from_server_name(cls, user, server_name):
        k8s_client, k8s_namespace = get_k8s_client()
        pods = get_all_user_pods(user, k8s_client, k8s_namespace)
        renku_annotation_prefix = "renku.io/"
        pods = filter_pods_by_annotations(
            pods, {"hub.jupyter.org/servername": server_name}
        )
        if len(pods) != 1:
            return None
        pod = pods[0]
        image = None
        for container in pod.spec.containers:
            if container.name == "notebook":
                image = container.image
        return cls(
            user,
            pod.get("metadata", {})
            .get("annotations", {})
            .get(renku_annotation_prefix + "namespace"),
            pod.get("metadata", {})
            .get("annotations", {})
            .get(renku_annotation_prefix + "projectName"),
            pod.get("metadata", {})
            .get("annotations", {})
            .get(renku_annotation_prefix + "branch"),
            pod.get("metadata", {})
            .get("annotations", {})
            .get(renku_annotation_prefix + "commit-sha"),
            None,
            image,
            {},
        )
