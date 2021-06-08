# -*- coding: utf-8 -*-
#
# Copyright 2019 - Swiss Data Science Center (SDSC)
# A partnership between École Polytechnique Fédérale de Lausanne (EPFL) and
# Eidgenössische Technische Hochschule Zürich (ETHZ).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Mocks and fixtures that are loaded automatically by pytest.

An instance of Traefik proxy is installed and started at the very
beginning of the whole test session. For each test, an instance of
JupyterHub is started along with an instance of the notebook-services
application. Gitlab and Kubernetes are mocked.
"""
import os
from unittest.mock import MagicMock
import pytest
import requests
import escapism
import base64
import json
from datetime import datetime

from jupyterhub.services.auth import HubOAuth
from tests.utils.classes import AttributeDictionary, CustomList


os.environ["GITLAB_URL"] = "https://gitlab-url.com"
os.environ["IMAGE_REGISTRY"] = "registry.gitlab-url.com"
os.environ["DEFAULT_IMAGE"] = "renku/singleuser:latest"
os.environ[
    "NOTEBOOKS_SERVER_OPTIONS_DEFAULTS_PATH"
] = "tests/unit/dummy_server_defaults.json"
os.environ["NOTEBOOKS_SERVER_OPTIONS_UI_PATH"] = "tests/unit/dummy_server_options.json"


@pytest.fixture
def app():
    os.environ[
        "NOTEBOOKS_SERVER_OPTIONS_DEFAULTS_PATH"
    ] = "tests/unit/dummy_server_defaults.json"
    os.environ["NOTEBOOKS_SERVER_OPTIONS_UI_PATH"] = "tests/unit/dummy_server_options.json"
    from renku_notebooks.wsgi import app

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def git_params():
    url = "git_url"
    auth_header = "Bearer token"
    return {url: {"AuthorizationHeader": auth_header}}


@pytest.fixture
def parsed_jwt():
    return {
        "sub": "userid",
        "email": "email",
        "iss": "oidc_issuer",
    }


@pytest.fixture
def proper_headers(parsed_jwt, git_params):
    return {
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


@pytest.fixture
def gitlab_projects():
    return AttributeDictionary({})


@pytest.fixture(autouse=True)
def gitlab(mocker, gitlab_projects):
    gitlab = mocker.patch("renku_notebooks.api.classes.user.Gitlab")
    gitlab_mock = MagicMock()
    gitlab_mock.auth = MagicMock()
    gitlab_mock.projects = gitlab_projects
    gitlab_mock.namespace = "namespace"
    gitlab_mock.user = AttributeDictionary(
        {"username": "namespace", "name": "John Doe"}
    )
    gitlab.return_value = gitlab_mock
    return gitlab


@pytest.fixture
def setup_project(gitlab_projects):
    def _setup_project(project_name, branches, commits, date_isostring):
        gitlab_projects[project_name] = AttributeDictionary(
            {
                "name": project_name,
                "commits": AttributeDictionary(
                    {commit: AttributeDictionary({"id": commit}) for commit in commits}
                ),
                "branches": CustomList(
                    *[
                        AttributeDictionary(
                            {
                                "name": branch,
                                "commit": AttributeDictionary(
                                    {"committed_date": date_isostring}
                                ),
                            }
                        )
                        for branch in branches
                    ],
                ),
            }
        )

    yield _setup_project


@pytest.fixture
def make_all_images_valid(mocker):
    mocker.patch("renku_notebooks.api.classes.server.image_exists").return_value = True
    mocker.patch("renku_notebooks.api.classes.server.get_docker_token").return_value = (
        "token",
        False,
    )


@pytest.fixture
def make_server_args_valid(mocker):
    mocker.patch(
        "renku_notebooks.api.notebooks.UserServer._project_exists"
    ).return_value = True
    mocker.patch(
        "renku_notebooks.api.notebooks.UserServer._branch_exists"
    ).return_value = True
    mocker.patch(
        "renku_notebooks.api.notebooks.UserServer._commit_sha_exists"
    ).return_value = True


def create_pod(username, server_name, payload):
    namespace = payload.get("namespace")
    project = payload.get("project")
    branch = payload.get("branch")
    commit_sha = payload.get("commit_sha")
    image = payload.get("image")
    safe_username = escapism.escape(username, escape_char="-").lower()
    return {
        "metadata": {
            "name": server_name,
            "annotations": {
                "hub.jupyter.org/servername": server_name,
                "hub.jupyter.org/username": username,
                "renku.io/branch": branch,
                "renku.io/commit-sha": commit_sha,
                "renku.io/git-host": os.environ.get("GIT_HOST", "git-host"),
                "renku.io/namespace": namespace,
                "renku.io/gitlabProjectId": "42",
                "renku.io/projectName": project,
                "renku.io/repository": (
                    f"{os.environ.get('GITLAB_URL', 'https:git-host.com')}/{namespace}/{project}"
                ),
                "renku.io/username": safe_username,
                "renku.io/default_image_used": image
                == os.environ.get("DEFAULT_IMAGE", "default_image"),
            },
            "labels": {
                "app": "jupyterhub",
                "chart": "jupyterhub-0.9-e120fda",
                "component": "singleuser-server",
                "heritage": "jupyterhub",
                "release": "dummy-renku",
                "renku.io/username": safe_username,
                "renku.io/commit-sha": commit_sha,
                "renku.io/projectName": project,
                "renku.io/gitlabProjectId": "42",
            },
        },
        "status": {
            "start_time": datetime.now(),
            "phase": "Running",
            "container_statuses": [{"ready": True}],
            "conditions": [
                {"type": "Initialized", "status": True, "message": "", "reason": ""},
                {"type": "Ready", "status": True, "message": "", "reason": ""},
                {
                    "type": "ContainersReady",
                    "status": True,
                    "message": "",
                    "reason": "",
                },
                {"type": "PodScheduled", "status": True, "message": "", "reason": ""},
            ],
        },
        "spec": {
            "containers": [
                {
                    "name": "notebook",
                    "image": image,
                    "resources": {
                        "requests": {
                            "cpu": "0.1",
                            "memory": "1G",
                            "ephemeral-storage": "5Gi",
                            "gpu": "1",
                        }
                    },
                }
            ]
        },
    }


@pytest.fixture
def pod_items():
    return AttributeDictionary({"items": []})


@pytest.fixture
def add_pod(pod_items):
    def _add_pod(pod):
        pod_items.items.append(pod)

    yield _add_pod


@pytest.fixture
def delete_pod(pod_items):
    def _delete_pod(pod_name):
        rem_items = list(filter(lambda x: x.metadata.name != pod_name, pod_items.items))
        pod_items.items.clear()
        pod_items.items.extend(rem_items)

    yield _delete_pod


@pytest.fixture
def kubernetes_client(mocker, delete_pod, pod_items):
    def force_delete_pod(*args, **kwargs):
        pod_name = args[0] if len(args) > 0 else kwargs["pod"]
        delete_pod(pod_name)

    res = mocker.MagicMock()
    res.list_namespaced_pod.return_value = pod_items
    res.read_namespaced_pod_log.return_value = "Some log"
    res.delete_namespaced_pod.side_effect = force_delete_pod
    # patch k8s client everywhere
    mocker.patch("renku_notebooks.util.kubernetes_.get_k8s_client").return_value = (
        res,
        "namespace",
    )
    mocker.patch("renku_notebooks.api.classes.server.get_k8s_client").return_value = (
        res,
        "namespace",
    )
    mocker.patch("renku_notebooks.api.classes.user.get_k8s_client").return_value = (
        res,
        "namespace",
    )
    mocker.patch("renku_notebooks.api.classes.storage.get_k8s_client").return_value = (
        res,
        "namespace",
    )


@pytest.fixture
def mock_server_start(mocker, add_pod):
    def _mock_server_start(self):
        payload = self._get_start_payload()
        pod = AttributeDictionary(
            create_pod(self._user.hub_username, self.server_name, payload)
        )
        jh_admin_auth = HubOAuth(
            api_token=os.environ.get("JUPYTERHUB_API_TOKEN", "token"), cache_max_age=60
        )
        headers = {jh_admin_auth.auth_header_name: f"token {jh_admin_auth.api_token}"}
        res = requests.post(
            f"{jh_admin_auth.api_url}/users/{self._user.hub_username}/servers/{self.server_name}",
            json=payload,
            headers=headers,
        )
        if res.status_code in [202, 201]:
            add_pod(pod)
        return res, None

    mocker.patch(
        "renku_notebooks.api.notebooks.UserServer.start", new=_mock_server_start
    )
