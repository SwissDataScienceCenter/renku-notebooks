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

from renku_notebooks.api.notebooks import create_named_server

os.environ["JUPYTERHUB_SERVICE_PREFIX"] = "/service"
os.environ["JUPYTERHUB_API_TOKEN"] = "03b0421755116015fe8b44d53d7fc0cc"
os.environ["JUPYTERHUB_CLIENT_ID"] = "client-id"


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
    os.environ["NOTEBOOKS_SERVER_OPTIONS_PATH"] = "tests/dummy_server_options.json"

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
        class List:
            def __init__(self, *args):
                self.__objects = list(args)

            def list(self):
                return self.__objects

            def items(self):
                return self.__objects

        gitlab_project = _AttributeDictionary(
            {
                f"{namespace}/{project_name}": {
                    "id": 42,
                    "visibility": "public",
                    "path_with_namespace": f"{namespace}/{project_name}",
                    "attributes": {
                        "permissions": List([{}, {"access_level": access_level}]),
                        "id": 42,
                        "visibility": "public",
                        "path_with_namespace": f"{namespace}/{project_name}",
                    },
                    "pipelines": List(
                        _AttributeDictionary(
                            {
                                "attributes": {"sha": ""},
                                "jobs": List(
                                    _AttributeDictionary(
                                        {"attributes": {"name": "", "status": ""}}
                                    )
                                ),
                            }
                        )
                    ),
                    "repositories": List(
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

    gitlab = mocker.patch("renku_notebooks.util.gitlab_.gitlab")

    project = mocker.MagicMock()
    project.projects = create_mock_gitlab_project(request.param[0], **request.param[1])
    gitlab.Gitlab.return_value = project
    gitlab.DEVELOPER_ACCESS = DEVELOPER_ACCESS

    gitlab.namespace = request.param[1].get("namespace")
    gitlab.project_name = request.param[1].get("project_name")

    return gitlab


@pytest.fixture
def make_all_images_valid(mocker):
    config = mocker.patch("renku_notebooks.api.notebooks.config")
    image_exists = mocker.patch("renku_notebooks.api.notebooks.image_exists")
    get_docker_token = mocker.patch("renku_notebooks.api.notebooks.get_docker_token")
    image_exists.return_value = True
    get_docker_token.return_value = "token", False
    config.IMAGE_REGISTRY = "image.registry"


def create_pod(user, server_name, payload):
    namespace = payload.get("namespace")
    project = payload.get("project")
    branch = payload.get("branch")
    commit_sha = payload.get("commit_sha")
    image = payload.get("image")
    server_options = payload.get("server_options")
    safe_username = escapism.escape(user.get("name"), escape_char="-").lower()
    return {
        "metadata": {
            "name": server_name,
            "annotations": {
                "hub.jupyter.org/servername": server_name,
                "hub.jupyter.org/username": user["name"],
                "renku.io/branch": branch,
                "renku.io/commit-sha": commit_sha,
                "renku.io/git-host": os.environ.get("GIT_HOST", "git-host"),
                "renku.io/namespace": namespace,
                "renku.io/projectId": "42",
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
                            "cpu": str(server_options["cpu_request"]),
                            "memory": str(server_options["mem_request"]),
                            "ephemeral-storage": str(
                                server_options.get("storage_request", "5Gi")
                            ),
                            "gpu": str(server_options.get("gpu", "1")),
                        }
                    },
                }
            ]
        },
    }


@pytest.fixture
def kubernetes_client(mocker):
    kubernetes_client_mock = mocker.MagicMock()
    kubernetes_client_mock.list_namespaced_pod.return_value = _AttributeDictionary(
        {"items": []}
    )
    kubernetes_client_mock.read_namespaced_pod_log.return_value = "some logs"
    get_k8s_client_mock = mocker.patch(
        "renku_notebooks.util.kubernetes_.get_k8s_client"
    )
    get_k8s_client_mock.return_value = kubernetes_client_mock, "namespace"

    def add_pod(*args, **kwargs):
        res = create_named_server(*args, **kwargs)
        pod = create_pod(*args, **kwargs)
        kubernetes_client_mock.list_namespaced_pod.return_value = _AttributeDictionary(
            {
                "items": kubernetes_client_mock.list_namespaced_pod.return_value.items
                + [pod]
            }
        )
        return res

    spawner_mock = mocker.patch(
        "renku_notebooks.api.notebooks.create_named_server", new=add_pod
    )

    def force_delete_pod(*args, **kwargs):
        pod_name = args[0] if len(args) > 0 else kwargs["pod"]
        items = kubernetes_client_mock.list_namespaced_pod.return_value.items
        items = list(filter(lambda x: x.metadata.name != pod_name, items))
        kubernetes_client_mock.list_namespaced_pod.return_value = _AttributeDictionary(
            {"items": items}
        )

    kubernetes_client_mock.delete_namespaced_pod.side_effect = force_delete_pod
    spawner_mock.side_effect = add_pod
