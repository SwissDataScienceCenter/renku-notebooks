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
import contextlib
import os
import pytest
import requests
import subprocess
import sys
import time
import escapism

from datetime import datetime
from gitlab import DEVELOPER_ACCESS
from jupyterhub.services.auth import HubOAuth

os.environ["JUPYTERHUB_SERVICE_PREFIX"] = "/service"
os.environ["JUPYTERHUB_PATH_PREFIX"] = "/jupyterhub"
os.environ["JUPYTERHUB_ORIGIN"] = ""
os.environ["JUPYTERHUB_API_TOKEN"] = "03b0421755116015fe8b44d53d7fc0cc"
os.environ["JUPYTERHUB_CLIENT_ID"] = "client-id"
os.environ["GITLAB_URL"] = "https://gitlab-url.com"
os.environ["IMAGE_REGISTRY"] = "registry.gitlab-url.com"
os.environ["DEFAULT_IMAGE"] = "renku/singleuser:latest"
os.environ[
    "NOTEBOOKS_SERVER_OPTIONS_DEFAULTS_PATH"
] = "tests/dummy_server_defaults.json"
os.environ["NOTEBOOKS_SERVER_OPTIONS_UI_PATH"] = "tests/dummy_server_options.json"
os.environ["NOTEBOOKS_SESSION_PVS_ENABLED"] = "false"


@pytest.fixture(scope="session", autouse=True)
def traefik():
    PROXY_BIN_DIR = os.path.join(os.path.dirname(__file__), ".proxy/")

    def install_traefik():
        subprocess.check_output(
            [
                "python3",
                "-m",
                "jupyterhub_traefik_proxy.install",
                "--output",
                PROXY_BIN_DIR,
                "--traefik",
            ]
        )

    install_traefik()

    proxy = subprocess.Popen(
        [os.path.join(PROXY_BIN_DIR, "traefik"), "-c", "tests/traefik.toml"],
        stdout=sys.stdout,
        stderr=subprocess.STDOUT,
    )

    yield proxy

    proxy.terminate()
    proxy.wait()


@pytest.fixture(autouse=True)
def jupyterhub(traefik):
    PROXY_PORT = 19000  # Make sure to change corresponding value in "traefik.toml"
    DEBUG_ENABLE_STDOUT = False

    def wait_for_jupyterhub_to_start():
        MAX_RETRIES = 50
        retries = 0
        while True:
            try:
                r = requests.get(f"http://localhost:{PROXY_PORT}/hub/api")
                if r.status_code == 200:
                    break
            except requests.exceptions.ConnectionError:
                pass
            retries += 1
            if retries > MAX_RETRIES:
                terminate_jupyterhub()
                raise RuntimeError(
                    "Cannot start JupyterHub for tests. "
                    "Make sure no other JupyterHub instance is running."
                )
            time.sleep(0.1)

    def terminate_jupyterhub():
        try:
            jupyterhub.terminate()
            jupyterhub.wait()
            with contextlib.suppress(FileNotFoundError):
                os.remove("jupyterhub_cookie_secret")
        except Exception:
            pass

    stdout = sys.stdout if DEBUG_ENABLE_STDOUT else subprocess.DEVNULL

    jupyterhub = subprocess.Popen(
        [
            "jupyterhub",
            "--no-db",
            "--port",
            str(PROXY_PORT),
            "--config",
            os.path.join(os.path.dirname(__file__), "dummy_jupyterhub_config.py"),
        ],
        stdout=stdout,
        stderr=subprocess.STDOUT,
    )

    wait_for_jupyterhub_to_start()

    yield jupyterhub

    terminate_jupyterhub()


@pytest.fixture
def client():
    os.environ[
        "NOTEBOOKS_SERVER_OPTIONS_DEFAULTS_PATH"
    ] = "tests/dummy_server_defaults.json"
    os.environ["NOTEBOOKS_SERVER_OPTIONS_UI_PATH"] = "tests/dummy_server_options.json"

    from renku_notebooks.wsgi import app

    client = app.test_client()
    return client


class _AttributeDictionary(dict):
    """Enables accessing dictionary keys as attributes"""

    def __init__(self, dictionary):
        for key, value in dictionary.items():
            # TODO check if key is a valid identifier
            if isinstance(value, dict):
                value = _AttributeDictionary(value)
            elif isinstance(value, list):
                value = [
                    _AttributeDictionary(v) if isinstance(v, dict) else v for v in value
                ]
            self.__setattr__(key, value)
            self[key] = value


class CustomList:
    def __init__(self, *args):
        self.__objects = list(args)

    def list(self):
        return self.__objects

    def items(self):
        return self.__objects

    def get(self, name):
        for i in self.__objects:
            if i.get("name") == name:
                return i


@pytest.fixture(
    params=[
        (
            DEVELOPER_ACCESS,
            {"namespace": "dummynamespace", "project_name": "dummyproject"},
        )
    ],
    autouse=True,
)
def gitlab(request, mocker):
    def create_mock_gitlab_project(
        access_level, namespace="dummynamespace", project_name="dummyproject"
    ):
        gitlab_project = _AttributeDictionary(
            {
                f"{namespace}/{project_name}": {
                    "id": 42,
                    "visibility": "public",
                    "path_with_namespace": f"{namespace}/{project_name}",
                    "attributes": {
                        "permissions": CustomList([{}, {"access_level": access_level}]),
                        "id": 42,
                        "visibility": "public",
                        "path_with_namespace": f"{namespace}/{project_name}",
                    },
                    "pipelines": CustomList(
                        _AttributeDictionary(
                            {
                                "attributes": {"sha": ""},
                                "jobs": CustomList(
                                    _AttributeDictionary(
                                        {"attributes": {"name": "", "status": ""}}
                                    )
                                ),
                            }
                        )
                    ),
                    "repositories": CustomList(
                        _AttributeDictionary(
                            {
                                "attributes": {
                                    "location": f"registry/{namespace}/{project_name}".lower(),
                                    "path": f"{namespace}/{project_name}".lower(),
                                },
                                "tags": {"0123456": ""},
                            }
                        )
                    ),
                }
            }
        )

        return gitlab_project

    gitlab = mocker.patch("renku_notebooks.api.classes.user.gitlab")

    project = mocker.MagicMock()
    project.projects = create_mock_gitlab_project(request.param[0], **request.param[1])
    gitlab.Gitlab.return_value = project
    gitlab.DEVELOPER_ACCESS = DEVELOPER_ACCESS

    gitlab.namespace = request.param[1].get("namespace")
    gitlab.project_name = request.param[1].get("project_name")

    return gitlab


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
            ],
            "volumes": [
                {
                    "name": server_name + "-git-repo",
                    "empty_dir": {
                        "size_limit": payload.get("serverOptions", {}).get(
                            "disk_request"
                        )
                    },
                }
            ],
        },
    }


@pytest.fixture
def pod_items():
    return _AttributeDictionary({"items": []})


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
        pod = _AttributeDictionary(
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
