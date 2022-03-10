from datetime import datetime, timedelta
import pytest
import os
import json
import base64
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)
from kubernetes.client.api import core_v1_api
from kubernetes.stream import stream
from gitlab import Gitlab
from gitlab.exceptions import GitlabDeleteError, GitlabGetError
import subprocess
from urllib.parse import urlparse
import escapism
import requests
from shlex import split as shlex_split
from time import sleep

from tests.integration.utils import find_session_pod, is_pod_ready, find_session_js


@pytest.fixture()
def anonymous_user_id():
    return "anonymoususerid"


@pytest.fixture(scope="session", autouse=True)
def load_k8s_config():
    InClusterConfigLoader(
        token_filename=SERVICE_TOKEN_FILENAME,
        cert_filename=SERVICE_CERT_FILENAME,
    ).load_and_set()


@pytest.fixture()
def k8s_namespace():
    return os.environ["KUBERNETES_NAMESPACE"]


@pytest.fixture(scope="session")
def is_gitlab_client_anonymous():
    def _is_gitlab_client_anonymous(client):
        if getattr(client, "user", None) is None:
            return True
        else:
            return False

    yield _is_gitlab_client_anonymous


@pytest.fixture()
def headers(anonymous_user_id, is_gitlab_client_anonymous, gitlab_client):
    if not is_gitlab_client_anonymous(gitlab_client):
        parsed_jwt = {
            "sub": "userid",
            "email": gitlab_client.user.email,
            "iss": os.environ["OIDC_ISSUER"],
            "name": gitlab_client.user.username,
            "preferred_username": gitlab_client.user.username,
        }
        git_params = {
            os.environ["GITLAB_URL"]: {
                "AuthorizationHeader": f"bearer {os.environ['GITLAB_TOKEN']}"
            }
        }
        headers = {
            "Renku-Auth-Id-Token": ".".join(
                [
                    base64.b64encode(json.dumps({}).encode()).decode(),
                    base64.b64encode(json.dumps(parsed_jwt).encode()).decode(),
                    base64.b64encode(json.dumps({}).encode()).decode(),
                ]
            ),
            "Renku-Auth-Git-Credentials": base64.b64encode(
                json.dumps(git_params).encode()
            ).decode(),
            "Renku-Auth-Access-Token": "test",
        }
    else:
        headers = {
            "Renku-Auth-Anon-Id": anonymous_user_id,
        }
    return headers


@pytest.fixture
def base_url():
    return os.environ["NOTEBOOKS_BASE_URL"] + "/notebooks"


@pytest.fixture(scope="session")
def registered_gitlab_client():
    client = Gitlab(
        os.environ["GITLAB_URL"], api_version=4, oauth_token=os.environ["GITLAB_TOKEN"]
    )
    client.auth()
    return client


@pytest.fixture(scope="session")
def anonymous_gitlab_client():
    client = Gitlab(os.environ["GITLAB_URL"], api_version=4)
    return client


@pytest.fixture(
    scope="session",
    params=[os.environ["SESSION_TYPE"]],
)
def gitlab_client(request, anonymous_gitlab_client, registered_gitlab_client):
    if request.param == "registered":
        return registered_gitlab_client
    else:
        return anonymous_gitlab_client


@pytest.fixture(scope="session")
def gitlab_project(
    registered_gitlab_client,
    gitlab_client,
    populate_test_project,
    is_gitlab_client_anonymous,
):
    tstamp = datetime.now().strftime("%y%m%d-%H%M%S")
    visibility = (
        "private" if not is_gitlab_client_anonymous(gitlab_client) else "public"
    )
    project_name = f"renku-notebooks-test-{tstamp}-{visibility}"
    project = registered_gitlab_client.projects.create(
        {"name": project_name, "visibility": visibility}
    )
    populate_test_project(project)
    yield project
    project.delete()  # clean up project when done
    sleep(10)


@pytest.fixture(scope="session")
def setup_git_creds():
    gitlab_host = urlparse(os.environ["GITLAB_URL"]).netloc
    # NOTE: git_cli cannot be used here because git_cli
    # depends on this step to setup the credentials
    subprocess.check_call(
        [
            "sh",
            "-c",
            "git config --global credential.helper 'store --file=/credentials'",
        ]
    )
    subprocess.check_call(
        [
            "sh",
            "-c",
            f"echo \"https://oauth2:{os.environ['GITLAB_TOKEN']}@{gitlab_host}\" > /credentials",
        ]
    )
    subprocess.check_call(
        ["git", "config", "--global", "user.name", "renku-notebooks-tests"]
    )
    subprocess.check_call(
        [
            "git",
            "config",
            "--global",
            "user.email",
            "renku-notebooks-tests@users.noreply.renku.ch",
        ]
    )


@pytest.fixture(scope="session")
def local_project_path(tmp_path_factory):
    return tmp_path_factory.mktemp("renku-tests-", numbered=True)


@pytest.fixture(scope="session")
def populate_test_project(setup_git_creds, local_project_path, git_cli):
    def _populate_test_project(gitlab_project):
        subprocess.check_call(
            shlex_split(
                "renku init --template-id minimal --template-ref master --template-source "
                "'https://github.com/SwissDataScienceCenter/renku-project-template'",
            ),
            cwd=local_project_path.absolute(),
        )
        git_cli(f"git remote add origin {gitlab_project.http_url_to_repo}")
        git_cli("git push origin master")

    yield _populate_test_project


@pytest.fixture
def timeout_mins():
    return int(os.environ.get("TIMEOUT_MINS", 10))


@pytest.fixture
def username(gitlab_client, anonymous_user_id, is_gitlab_client_anonymous):
    if is_gitlab_client_anonymous(gitlab_client):
        # user is anonymous
        return anonymous_user_id
    else:
        # user is not anonymous
        return gitlab_client.user.username


@pytest.fixture
def safe_username(username):
    return escapism.escape(username, escape_char="-").lower()


@pytest.fixture
def ci_jobs_completed_on_time(timeout_mins, gitlab_project):
    completed_statuses = ["success", "failed", "canceled", "skipped"]

    def _ci_jobs_completed_on_time(timeout_mins=timeout_mins):
        tstart = datetime.now()
        while True:
            print("Waiting for CI jobs to finish.")
            try:
                # NOTE: Sometimes this call fails with connection error which then fails
                # all the tests - to avoid this scenario try to sleep a bit and retry
                job_list = gitlab_project.jobs.list(all=True)
            except requests.exceptions.ConnectionError:
                sleep(3)
                job_list = gitlab_project.jobs.list(all=True)
            all_jobs_done = (
                all(
                    [
                        job.status in completed_statuses
                        for job in job_list
                    ]
                )
                and len(job_list) >= 1
            )
            if not all_jobs_done and datetime.now() - tstart > timedelta(
                minutes=timeout_mins
            ):
                print("Waiting for CI jobs to complete timed out.")
                return False  # waiting for ci jobs to complete timed out
            if all_jobs_done:
                return True
            sleep(10)

    yield _ci_jobs_completed_on_time


@pytest.fixture
def launch_session(
    base_url,
    k8s_namespace,
    timeout_mins,
    safe_username,
    delete_session,
    ci_jobs_completed_on_time,
):
    launched_sessions = []

    def _launch_session(payload, test_gitlab_project, test_headers, wait_for_ci=True):
        # wait for all ci/cd jobs to finish
        if wait_for_ci:
            assert ci_jobs_completed_on_time()
            print("CI jobs finished")
        response = requests.post(
            f"{base_url}/servers", headers=test_headers, json=payload
        )
        # if session launched successfully wait for it to become fully ready
        if response.status_code < 300:
            session_dict = {
                "session": response.json(),
                "test_gitlab_project": test_gitlab_project,
                "test_headers": test_headers,
            }
            if session_dict not in launched_sessions:
                launched_sessions.append(session_dict)
            tstart = datetime.now()
            while True:
                pod = find_session_pod(
                    test_gitlab_project,
                    k8s_namespace,
                    safe_username,
                    payload["commit_sha"],
                    payload.get("branch", "master"),
                )
                pod_ready = is_pod_ready(pod)
                if not pod_ready and datetime.now() - tstart > timedelta(
                    minutes=timeout_mins
                ):
                    print("Witing for server to be ready timed out.")
                    return None  # waiting for pod to fully become ready timed out
                if pod_ready:
                    return response
                sleep(10)
        print("The server is ready for testing.")
        return response

    yield _launch_session
    for kwargs in launched_sessions:
        delete_session(**kwargs)


@pytest.fixture
def delete_session(base_url, k8s_namespace, safe_username, timeout_mins):
    def _delete_session(session, test_gitlab_project, test_headers):
        session_name = session["name"]
        response = requests.delete(
            f"{base_url}/servers/{session_name}", headers=test_headers
        )
        if response.status_code < 300:
            tstart = datetime.now()
            while True:
                pod = find_session_pod(
                    test_gitlab_project,
                    k8s_namespace,
                    safe_username,
                    session["annotations"]["renku.io/commit-sha"],
                    session["annotations"]["renku.io/branch"],
                )
                js = find_session_js(
                    test_gitlab_project,
                    k8s_namespace,
                    safe_username,
                    session["annotations"]["renku.io/commit-sha"],
                    session["annotations"]["renku.io/branch"],
                )
                if (
                    datetime.now() - tstart > timedelta(minutes=timeout_mins)
                    and pod is not None
                    and js is not None
                ):
                    return None  # waiting for pod to be shut down timed out
                if pod is None and js is None:
                    return response
                sleep(10)
        return response

    yield _delete_session


@pytest.fixture
def valid_payload(gitlab_project):
    try:
        gitlab_project.commits.get("HEAD")
    except GitlabGetError:
        sleep(10)
    yield {
        "commit_sha": gitlab_project.commits.get("HEAD").id,
        "namespace": gitlab_project.namespace["full_path"],
        "project": gitlab_project.path,
    }


@pytest.fixture(scope="session")
def server_options_ui():
    server_options_file = os.getenv(
        "NOTEBOOKS_SERVER_OPTIONS_UI_PATH",
        "/etc/renku-notebooks/server_options/server_options.json",
    )
    with open(server_options_file) as f:
        server_options = json.load(f)

    return server_options


@pytest.fixture
def create_remote_branch(registered_gitlab_client, gitlab_project):
    created_branches = []

    def _create_remote_branch(branch_name, ref="HEAD"):
        # always user the registered client to create branches
        # the anonymous client does not have the permissions to do so
        project = registered_gitlab_client.projects.get(gitlab_project.id)
        branch = project.branches.create({"branch": branch_name, "ref": ref})
        created_branches.append(branch)
        return branch

    yield _create_remote_branch

    for branch in created_branches:
        project = registered_gitlab_client.projects.get(branch.project_id)
        pipelines = project.pipelines.list()
        for pipeline in pipelines:
            if pipeline.sha == branch.commit["id"] and pipeline.ref == branch.name:
                pipeline.cancel()
                try:
                    pipeline.delete()
                except GitlabDeleteError:
                    pass
        branch.delete()


@pytest.fixture(scope="session")
def git_cli(setup_git_creds, local_project_path):
    def _git_cli(cmd):
        return subprocess.check_output(shlex_split(cmd), cwd=local_project_path)

    yield _git_cli


@pytest.fixture(scope="session")
def pod_exec(load_k8s_config):
    """
        Execute the specific command
        in the speicific namespace/pod/container and return the results.
    """
    def _pod_exec(k8s_namespace, session_name, container, command):
        pod_name = f"{session_name}-0"
        api = core_v1_api.CoreV1Api()
        resp = stream(
            api.connect_get_namespaced_pod_exec,
            pod_name,
            k8s_namespace,
            command=shlex_split(command),
            container=container,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=True,
        )
        if type(resp) is bytes:
            resp = resp.decode()
        return resp

    yield _pod_exec
