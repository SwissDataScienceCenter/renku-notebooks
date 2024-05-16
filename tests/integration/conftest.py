import base64
import contextlib
import json
import os
import subprocess
from datetime import datetime, timedelta
from itertools import chain, repeat
from shlex import split as shlex_split
from time import sleep, time
from urllib.parse import urlparse
from uuid import uuid4

import escapism
import pytest
import requests
from gitlab import Gitlab
from gitlab.exceptions import GitlabDeleteError, GitlabGetError
from kubernetes.client.api import core_v1_api
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)
from kubernetes.stream import stream

from renku_notebooks.config import config
from tests.integration.utils import find_session_js, find_session_pod, is_pod_ready


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
    sessions_namespace = os.environ.get("NB_K8S__SESSIONS_NAMESPACE")
    if sessions_namespace:
        return sessions_namespace
    return os.environ["NB_K8S__RENKU_NAMESPACE"]


@pytest.fixture(scope="session")
def is_gitlab_client_anonymous():
    def _is_gitlab_client_anonymous(client):
        return getattr(client, "user", None) is None

    yield _is_gitlab_client_anonymous


@pytest.fixture
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
            config.git.url: {
                "AuthorizationHeader": f"bearer {os.environ['GITLAB_TOKEN']}",
                "AccessTokenExpiresAt": int(time()) + 9999999999,
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
            "Renku-Auth-Git-Credentials": base64.b64encode(json.dumps(git_params).encode()).decode(),
            "Renku-Auth-Access-Token": "test",
            "Renku-Auth-Refresh-Token": "test-refresh-token",
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
        config.git.url,
        api_version="4",
        oauth_token=os.environ["GITLAB_TOKEN"],
        per_page=50,
    )
    client.auth()
    return client


@pytest.fixture(scope="session")
def anonymous_gitlab_client():
    client = Gitlab(config.git.url, api_version="4", per_page=50)
    return client


@pytest.fixture(
    scope="session",
    params=[os.environ.get("SESSION_TYPE")],
)
def gitlab_client(request, anonymous_gitlab_client, registered_gitlab_client):
    if request.param == "registered":
        return registered_gitlab_client
    else:
        return anonymous_gitlab_client


@pytest.fixture(scope="session")
def create_gitlab_project(
    registered_gitlab_client,
    gitlab_client,
    populate_test_project,
    is_gitlab_client_anonymous,
):
    created_projects = []

    def _create_gitlab_project(project_name=None, LFS_size_megabytes=0):
        tstamp = datetime.now().strftime("%y%m%d-%H%M%S")
        visibility = "private" if not is_gitlab_client_anonymous(gitlab_client) else "public"
        if project_name is None:
            project_name = f"renku-notebooks-test-{tstamp}-{visibility}"
        project = registered_gitlab_client.projects.create({"name": project_name, "visibility": visibility})
        print(f"Created project {project_name}")
        populate_test_project(project, LFS_size_megabytes)
        print(f"Populated project {project_name}")
        head_commit = None
        count = 0
        max_retries = 10
        while head_commit is None:
            print(f"Confirming git project creation for {project_name}")
            count += 1
            try:
                head_commit = project.commits.get("HEAD")
            except GitlabGetError:
                if count > max_retries:
                    raise
                else:
                    sleep(2)
        created_projects.append(project)
        return project

    yield _create_gitlab_project
    # NOTE: No need to delete local project folders - pytest takes care of that
    # because we use temporary pytest folders.
    [iproject.delete() for iproject in created_projects]


@pytest.fixture(scope="session")
def gitlab_project(create_gitlab_project):
    return create_gitlab_project()


@pytest.fixture(scope="session")
def setup_git_creds(tmp_dir):
    gitlab_host = urlparse(config.git.url).netloc
    # NOTE: git_cli cannot be used here because git_cli
    # depends on this step to set up the credentials
    credentials_path = tmp_dir / "credentials"
    subprocess.check_call(
        shlex_split(f"git config --global credential.helper 'store --file={credentials_path.absolute()}'")
    )
    with open(credentials_path, "w") as fout:
        fout.write(f"https://oauth2:{os.environ['GITLAB_TOKEN']}@{gitlab_host}")
        fout.write("\n")
    subprocess.check_call(shlex_split("git config --global user.name renku-notebooks-tests"))
    subprocess.check_call(
        shlex_split(
            "git config --global user.email renku-notebooks-tests@users.noreply.renku.ch",
        )
    )


@pytest.fixture(scope="session")
def tmp_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("renku-tests-", numbered=True)


@pytest.fixture(scope="session")
def local_project_path(tmp_dir):
    project_loc = tmp_dir / "local_project"
    project_loc.mkdir(parents=True, exist_ok=True)
    return project_loc


@pytest.fixture(scope="session")
def populate_test_project(setup_git_creds, git_cli, local_project_path):
    def _populate_test_project(gitlab_project, LFS_size_megabytes=0):
        INDIVIDUAL_LFS_FILE_MAX_SIZE_MB = 500
        # NOTE: This is here because we need all results of // and % to be ints
        # Python will happily reuturn a float when you do 5 // 2.0 or 5 % 2.0
        LFS_size_megabytes = int(LFS_size_megabytes)
        # INFO: Renku init
        subprocess.check_call(
            shlex_split(
                "renku init --template-id minimal --template-ref master --template-source "
                "https://github.com/SwissDataScienceCenter/renku-project-template"
            ),
            cwd=local_project_path,
        )
        # INFO: Generate LFS files (if needed)
        if LFS_size_megabytes > 0:
            file_sizes_to_create = repeat(
                INDIVIDUAL_LFS_FILE_MAX_SIZE_MB,
                LFS_size_megabytes // INDIVIDUAL_LFS_FILE_MAX_SIZE_MB,
            )
            if LFS_size_megabytes % INDIVIDUAL_LFS_FILE_MAX_SIZE_MB > 0:
                file_sizes_to_create = chain(
                    file_sizes_to_create,
                    [LFS_size_megabytes % INDIVIDUAL_LFS_FILE_MAX_SIZE_MB],
                )
            for file_size in file_sizes_to_create:
                file_name = f"{uuid4()}-data-file.bin"
                subprocess.check_call(
                    shlex_split(f"head -c {file_size}M < /dev/urandom > {file_name}"),
                    cwd=local_project_path,
                )
            git_cli("git lfs track *-data-file.bin")
        # INFO: Commit and push
        git_cli(f"git remote add origin {gitlab_project.http_url_to_repo}")
        git_cli("git push origin master")

    yield _populate_test_project


@pytest.fixture
def default_timeout_mins():
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
def ci_jobs_completed_on_time(default_timeout_mins):
    completed_statuses = ["success", "failed", "canceled", "skipped"]

    def _ci_jobs_completed_on_time(gitlab_project, timeout_mins=default_timeout_mins):
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
            all_jobs_done = all([job.status in completed_statuses for job in job_list]) and len(job_list) >= 1
            if not all_jobs_done and datetime.now() - tstart > timedelta(minutes=timeout_mins):
                print("Waiting for CI jobs to complete timed out.")
                return False  # waiting for ci jobs to complete timed out
            if all_jobs_done:
                return True
            sleep(10)

    yield _ci_jobs_completed_on_time


@pytest.fixture
def delete_session(base_url, k8s_namespace, safe_username, default_timeout_mins):
    def _delete_session(session, test_gitlab_project, test_headers, forced=False):
        session_name = session["name"]
        response = requests.delete(
            f"{base_url}/servers/{session_name}",
            headers=test_headers,
            params={"forced": "true" if forced else "false"},
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
                    datetime.now() - tstart > timedelta(minutes=default_timeout_mins)
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
def launch_session(
    base_url,
    ci_jobs_completed_on_time,
    default_timeout_mins,
    delete_session,
    headers,
    gitlab_project,
):
    """Launch a session. Please note that the scope of this fixture must be
    `function` - i.e. the default scope. If the scope is changed to a more global
    level then sessions launched with this fixture will accumulate. In CI pipeliens,
    especially on Github this can quickly exhaust all resources.
    """
    launched_sessions = []

    def _launch_session(
        test_headers,
        payload,
        test_gitlab_project,
        timeout_mins=default_timeout_mins,
        wait_for_ci=True,
    ):
        if wait_for_ci:
            assert ci_jobs_completed_on_time(test_gitlab_project, timeout_mins)
            print("CI jobs finished")
        response = requests.post(
            f"{base_url}/servers",
            headers=test_headers,
            json=payload,
        )
        print("Launched session")
        if response.status_code in [200, 201, 202]:
            launched_sessions.append(response)
        return response

    yield _launch_session
    for session in launched_sessions:
        session_name = session.json()["name"]
        print(f"Starting to delete session {session_name}")
        delete_session(session.json(), gitlab_project, headers)
        print(f"Finished deleting session {session_name}")


@pytest.fixture
def start_session_and_wait_until_ready(
    k8s_namespace,
    default_timeout_mins,
    safe_username,
    launch_session,
):
    def _start_session_and_wait_until_ready(
        test_headers, payload, test_gitlab_project, timeout_mins=default_timeout_mins
    ):
        response = launch_session(test_headers, payload, test_gitlab_project)
        # if session launched successfully wait for it to become fully ready
        if response.status_code < 300:
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
                if not pod_ready and datetime.now() - tstart > timedelta(minutes=timeout_mins):
                    print("Waiting for server to be ready timed out.")
                    return None  # waiting for pod to fully become ready timed out
                if pod_ready:
                    return response
                sleep(10)
        print("The server is ready for testing.")
        return response

    yield _start_session_and_wait_until_ready


@pytest.fixture(scope="session")
def get_valid_payload():
    def _get_valid_payload(gitlab_project):
        print(f"Getting valid payload from gitlab project {gitlab_project.name}")
        return {
            "commit_sha": gitlab_project.commits.get("HEAD").id,
            "namespace": gitlab_project.namespace["full_path"],
            "project": gitlab_project.path,
        }

    yield _get_valid_payload


@pytest.fixture(scope="session")
def valid_payload(gitlab_project, get_valid_payload):
    return get_valid_payload(gitlab_project)


@pytest.fixture(scope="session")
def server_options_ui():
    return config.server_options.ui_choices


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
        pipelines = project.pipelines.list(iterator=True)
        for pipeline in pipelines:
            if pipeline.sha == branch.commit["id"] and pipeline.ref == branch.name:
                pipeline.cancel()
                with contextlib.suppress(GitlabDeleteError):
                    pipeline.delete()
        branch.delete()


@pytest.fixture(scope="session")
def git_cli(setup_git_creds, local_project_path):
    def _git_cli(cmd):
        return subprocess.check_output(shlex_split(cmd), cwd=local_project_path)

    yield _git_cli


@pytest.fixture(scope="session")
def pod_exec(load_k8s_config):
    """Execute the specific command
    in the specific namespace/pod/container and return the results.
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
        if isinstance(resp, bytes):
            resp = resp.decode()
        return resp

    yield _pod_exec
