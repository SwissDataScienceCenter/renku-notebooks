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
import subprocess
from urllib.parse import urlparse
import escapism
import requests
from time import sleep

from tests.integration.utils import find_session_pod, is_pod_ready, find_session_crd


@pytest.fixture(scope="session", autouse=True)
def load_k8s_config():
    InClusterConfigLoader(
        token_filename=SERVICE_TOKEN_FILENAME, cert_filename=SERVICE_CERT_FILENAME,
    ).load_and_set()


@pytest.fixture()
def k8s_namespace():
    return os.environ["KUBERNETES_NAMESPACE"]


@pytest.fixture()
def headers():
    parsed_jwt = {
        "sub": "userid",
        "email": "email",
        "iss": os.environ["OIDC_ISSUER"],
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
    return headers


@pytest.fixture
def base_url():
    return os.environ["NOTEBOOKS_BASE_URL"] + "/notebooks"


@pytest.fixture(scope="session", autouse=True)
def gitlab_client():
    client = Gitlab(
        os.environ["GITLAB_URL"], api_version=4, oauth_token=os.environ["GITLAB_TOKEN"]
    )
    client.auth()
    return client


@pytest.fixture(scope="session", autouse=True)
def gitlab_project(gitlab_client, populate_test_project):
    tstamp = datetime.now().strftime("%y%m%d-%H%M%S")
    project_name = f"renku-notebooks-test-{tstamp}"
    project = gitlab_client.projects.create({"name": project_name, "visibility": "private"})
    populate_test_project(project, "test-project-private")
    yield project
    project.delete()  # clean up project when done


@pytest.fixture(scope="session", autouse=True)
def public_gitlab_project(gitlab_client, populate_test_project):
    tstamp = datetime.now().strftime("%y%m%d-%H%M%S")
    project_name = f"renku-notebooks-test-public-{tstamp}"
    project = gitlab_client.projects.create({"name": project_name, "visibility": "public"})
    populate_test_project(project, "test-project-public")
    yield project
    project.delete()  # clean up project when done


@pytest.fixture(scope="session", autouse=True)
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


@pytest.fixture(scope="session", autouse=True)
def tmp_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("renku-tests-", numbered=True)


@pytest.fixture(scope="session", autouse=True)
def renku_template(setup_git_creds, tmp_dir):
    templates_dir = tmp_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        [
            "git",
            "clone",
            "-q",
            "https://github.com/SwissDataScienceCenter/renku-project-template.git",
            templates_dir.absolute(),
        ]
    )
    return templates_dir / "minimal"


@pytest.fixture(scope="session", autouse=True)
def populate_test_project(setup_git_creds, tmp_dir, renku_template):
    def _populate_test_project(gitlab_project, project_folder="test_project"):
        project_loc = tmp_dir / project_folder
        subprocess.check_call(["cp", "-r", renku_template, project_loc])
        subprocess.check_call(["sh", "-c", f"cd {project_loc.absolute()} && git init"])
        subprocess.check_call(
            [
                "sh",
                "-c",
                f"cd {project_loc.absolute()} && "
                f"git remote add origin {gitlab_project.http_url_to_repo}",
            ]
        )
        subprocess.check_call(["sh", "-c", f"cd {project_loc.absolute()} && git add ."])
        subprocess.check_call(
            [
                "sh",
                "-c",
                f"cd {project_loc.absolute()} && git commit -m 'Intialized renku project'",
            ]
        )
        subprocess.check_call(
            ["sh", "-c", f"cd {project_loc.absolute()} && git push origin master"]
        )
        return project_loc

    yield _populate_test_project


@pytest.fixture
def timeout_mins():
    return os.environ.get("TIMEOUT_MINS", 10)


@pytest.fixture
def safe_username(gitlab_client):
    return escapism.escape(gitlab_client.user.username, escape_char="-").lower()


@pytest.fixture
def launch_session(
    base_url,
    headers,
    k8s_namespace,
    gitlab_project,
    timeout_mins,
    safe_username,
    delete_session,
):
    completed_statuses = ["success", "failed", "cancelled", "skipped"]
    launched_sessions = []

    def _launch_session(payload, headers=headers):
        # wait for all ci/cd jobs to finish
        tstart = datetime.now()
        while True:
            all_jobs_done = (
                all(
                    [
                        job.status in completed_statuses
                        for job in gitlab_project.jobs.list()
                    ]
                )
                and len(gitlab_project.jobs.list()) >= 1
            )
            if not all_jobs_done and datetime.now() - tstart > timedelta(
                minutes=timeout_mins
            ):
                return None  # waiting for ci jobs to complete timed out
            if all_jobs_done:
                break
            sleep(10)
        response = requests.post(f"{base_url}/servers", headers=headers, json=payload)
        # if session launched successfully wait for it to become fully ready
        if response.status_code < 300:
            launched_sessions.append(response.json())
            tstart = datetime.now()
            while True:
                pod = find_session_pod(
                    gitlab_project, k8s_namespace, safe_username, payload["commit_sha"]
                )
                pod_ready = is_pod_ready(pod)
                if not pod_ready and datetime.now() - tstart > timedelta(
                    minutes=timeout_mins
                ):
                    return None  # waiting for pod to fully become ready timed out
                if pod_ready:
                    return response
                sleep(10)
        return response

    yield _launch_session
    for session in launched_sessions:
        delete_session(session)


@pytest.fixture
def delete_session(
    base_url, headers, gitlab_project, k8s_namespace, safe_username, timeout_mins
):
    def _delete_session(session):
        session_name = session["name"]
        response = requests.delete(
            f"{base_url}/servers/{session_name}", headers=headers
        )
        if response.status_code < 300:
            tstart = datetime.now()
            while True:
                pod = find_session_pod(
                    gitlab_project,
                    k8s_namespace,
                    safe_username,
                    session["annotations"]["renku.io/commit-sha"],
                )
                crd = find_session_crd(
                    gitlab_project,
                    k8s_namespace,
                    safe_username,
                    session["annotations"]["renku.io/commit-sha"],
                )
                if (
                    datetime.now() - tstart > timedelta(minutes=timeout_mins)
                    and pod is not None
                    and crd is not None
                ):
                    return None  # waiting for pod to be shut down timed out
                if pod is None and crd is None:
                    return response
                sleep(10)
        return response

    yield _delete_session


@pytest.fixture
def valid_payload(gitlab_project):
    yield {
        "commit_sha": gitlab_project.commits.get("HEAD").id,
        "namespace": gitlab_project.namespace["full_path"],
        "project": gitlab_project.path,
    }


@pytest.fixture(scope="session", autouse=True)
def server_options_ui():
    server_options_file = os.getenv(
        "NOTEBOOKS_SERVER_OPTIONS_UI_PATH",
        "/etc/renku-notebooks/server_options/server_options.json",
    )
    with open(server_options_file) as f:
        server_options = json.load(f)

    return server_options