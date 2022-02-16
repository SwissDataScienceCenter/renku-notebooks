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
from gitlab import Gitlab
from gitlab.exceptions import GitlabDeleteError, GitlabGetError
import subprocess
from urllib.parse import urlparse
import escapism
import requests
from time import sleep
from itertools import repeat, chain
from uuid import uuid4

from tests.integration.utils import delete_session_js, find_session_pod, is_pod_ready


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
def create_gitlab_project(
    registered_gitlab_client,
    gitlab_client,
    populate_test_project,
    is_gitlab_client_anonymous,
):
    created_projects = []

    def _create_gitlab_project(project_name=None, LFS_size_megabytes=0):
        tstamp = datetime.now().strftime("%y%m%d-%H%M%S")
        visibility = (
            "private" if not is_gitlab_client_anonymous(gitlab_client) else "public"
        )
        if project_name is None:
            project_name = f"renku-notebooks-test-{tstamp}-{visibility}"
        project = registered_gitlab_client.projects.create(
            {"name": project_name, "visibility": visibility}
        )
        print(f"Created project {project_name}")
        populate_test_project(project, project_name, LFS_size_megabytes)
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
    # NOTE: No need to delete local projet folders - pytest takes care of that
    # beacuse we user temporary pytest folders.
    [iproject.delete() for iproject in created_projects]


@pytest.fixture(scope="session")
def gitlab_project(
    create_gitlab_project,
):
    return create_gitlab_project()


@pytest.fixture(scope="session")
def setup_git_creds():
    gitlab_host = urlparse(os.environ["GITLAB_URL"]).netloc
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
def tmp_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("renku-tests-", numbered=True)


@pytest.fixture(scope="session")
def populate_test_project(setup_git_creds, tmp_dir):
    def _populate_test_project(
        gitlab_project, project_folder="test_project", LFS_size_megabytes=0
    ):
        project_loc = tmp_dir / project_folder
        project_loc.mkdir(parents=True, exist_ok=True)
        INDIVIDUAL_LFS_FILE_MAX_SIZE_MB = 500
        # NOTE: This is here because we need all results of // and % to be ints
        # Python will happily reuturn a float when you do 5 // 2.0 or 5 % 2.0
        LFS_size_megabytes = int(LFS_size_megabytes)
        # INFO: Renku init
        subprocess.check_call(
            [
                "sh",
                "-c",
                f"cd {project_loc.absolute()} && "
                "renku init --template-id minimal --template-ref master --template-source "
                "https://github.com/SwissDataScienceCenter/renku-project-template",
            ]
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
                    [
                        "sh",
                        "-c",
                        f"head -c {file_size}M < /dev/urandom > "
                        f"{project_loc.absolute() / file_name}",
                    ]
                )
            subprocess.check_call(
                [
                    "sh",
                    "-c",
                    f"cd {project_loc.absolute()} && git lfs track *-data-file.bin",
                ]
            )
        # INFO: Commit and push
        subprocess.check_call(
            [
                "sh",
                "-c",
                f"cd {project_loc.absolute()} && "
                f"git remote add origin {gitlab_project.http_url_to_repo}",
            ]
        )
        subprocess.check_call(
            ["sh", "-c", f"cd {project_loc.absolute()} && git push origin master"]
        )
        return project_loc

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
    k8s_namespace, base_url, ci_jobs_completed_on_time, default_timeout_mins
):
    """Launch a session. Please note that the scope of this fixture must be
    `function` - i.e. the default scope. If the scope is changed to a more global
    level then sessions launched with this fixture will accumulate. In CI pipeliens,
    especially on Github this can quickly exhaust all resources."""
    launched_sessions = []

    def _launch_session(
        headers,
        payload,
        gitlab_project,
        timeout_mins=default_timeout_mins,
        wait_for_ci=True,
    ):
        if wait_for_ci:
            assert ci_jobs_completed_on_time(gitlab_project, timeout_mins)
            print("CI jobs finished")
        response = requests.post(
            f"{base_url}/servers",
            headers=headers,
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
        delete_session_js(session_name, k8s_namespace)
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
                if not pod_ready and datetime.now() - tstart > timedelta(
                    minutes=timeout_mins
                ):
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
    server_options_file = os.getenv(
        "NOTEBOOKS_SERVER_OPTIONS_UI_PATH",
        "/etc/renku-notebooks/server_options/server_options.json",
    )
    with open(server_options_file) as f:
        server_options = json.load(f)

    return server_options


@pytest.fixture
def create_branch(registered_gitlab_client, gitlab_project):
    created_branches = []

    def _create_branch(branch_name, ref="HEAD"):
        # always user the registered client to create branches
        # the anonymous client does not have the permissions to do so
        project = registered_gitlab_client.projects.get(gitlab_project.id)
        branch = project.branches.create({"branch": branch_name, "ref": ref})
        created_branches.append(branch)
        return branch

    yield _create_branch

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
