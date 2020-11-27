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
"""Tests for Notebook Services API"""
from gitlab import DEVELOPER_ACCESS
import pytest
from unittest.mock import patch, MagicMock

from renku_notebooks.util.jupyterhub_ import make_server_name


AUTHORIZED_HEADERS = {"Authorization": "token 8f7e09b3bf6b8a20"}
SERVER_NAME = make_server_name("dummynamespace", "dummyproject", "master", "0123456789")
NON_DEVELOPER_ACCESS = DEVELOPER_ACCESS - 1
DEFAULT_PAYLOAD = {
    "namespace": "dummynamespace",
    "project": "dummyproject",
    "commit_sha": "0123456789",
}


def create_notebook(client, **payload):
    print("CALLED with", payload)
    response = client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    return response


def create_notebook_with_default_parameters(client, **kwargs):
    return create_notebook(client, **DEFAULT_PAYLOAD, **kwargs,)


def test_can_check_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_can_create_notebooks(client, make_all_images_valid, kubernetes_client_full):
    response = create_notebook_with_default_parameters(client)
    assert response.status_code == 202 or response.status_code == 201


def test_can_get_created_notebooks(client, kubernetes_client_full):
    create_notebook_with_default_parameters(client)

    response = client.get("/service/servers", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert SERVER_NAME in response.json.get("servers")


def test_can_get_server_status_for_created_notebooks(client, kubernetes_client_full):
    create_notebook_with_default_parameters(client)

    response = client.get(f"/service/servers/{SERVER_NAME}", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json.get("name") == SERVER_NAME


def test_getting_notebooks_returns_nothing_when_no_notebook_is_created(
    client, kubernetes_client_empty
):
    response = client.get("/service/servers", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json.get("servers") == {}


def test_can_get_pods_logs(client, kubernetes_client_full):
    create_notebook_with_default_parameters(client)

    headers = AUTHORIZED_HEADERS.copy()
    response = client.get(f"/service/logs/{SERVER_NAME}", headers=headers)
    assert response.status_code == 200


def test_can_delete_created_notebooks(client, kubernetes_client_full):
    create_notebook_with_default_parameters(client)

    response = client.delete(
        f"/service/servers/{SERVER_NAME}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 204


def test_can_force_delete_created_notebooks(client, kubernetes_client_full):
    create_notebook_with_default_parameters(client)

    response = client.delete(
        f"/service/servers/{SERVER_NAME}",
        query_string={"force": "true"},
        headers=AUTHORIZED_HEADERS,
    )
    assert response.status_code == 204

    response = client.get("/service/servers", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json.get("servers") == {}


def test_recreating_notebooks_return_current_server(
    client, kubernetes_client_full, make_all_images_valid
):
    create_notebook_with_default_parameters(client)

    response = create_notebook_with_default_parameters(client)
    assert response.status_code == 200
    assert SERVER_NAME in response.json.get("name")


def test_can_create_notebooks_on_different_branches(
    client, kubernetes_client_empty, make_all_images_valid
):
    create_notebook_with_default_parameters(client, branch="branch")

    response = create_notebook_with_default_parameters(client, branch="another-branch")
    assert response.status_code == 201 or response.status_code == 202


@pytest.mark.parametrize(
    "payload",
    [
        {"project": "dummyproject", "commit_sha": "0123456789"},
        {"namespace": "dummynamespace", "commit_sha": "0123456789"},
        {"namespace": "dummynamespace", "project": "dummyproject"},
    ],
)
def test_creating_servers_with_incomplete_data_returns_400(
    client, kubernetes_client_empty, payload
):
    response = create_notebook(client, **payload)
    assert response.status_code == 400


def test_can_get_server_options(client, kubernetes_client_full):
    response = client.get("/service/server_options", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json == {"dummy-key": {"default": "dummy-value"}}


@pytest.mark.parametrize(
    "gitlab",
    [
        (
            NON_DEVELOPER_ACCESS,
            {"namespace": "dummynamespace", "project_name": "dummyproject"},
        )
    ],
    indirect=True,
)
def test_users_with_no_developer_access_can_create_notebooks(
    client, gitlab, make_all_images_valid, kubernetes_client_empty,
):
    response = create_notebook(
        client, **{**DEFAULT_PAYLOAD, "commit_sha": "5648434fds89"}
    )
    assert response.status_code == 202 or response.status_code == 201


def test_getting_logs_for_nonexisting_notebook_returns_404(
    client, kubernetes_client_empty
):
    response = client.get("/service/logs/non-existing-hash", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 404


def test_using_extra_slashes_in_notebook_url_results_in_308(
    client, kubernetes_client_empty
):
    SERVER_URL_WITH_EXTRA_SLASHES = f"/{SERVER_NAME}"
    response = client.post(
        f"/service/servers/{SERVER_URL_WITH_EXTRA_SLASHES}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 308


def test_deleting_nonexisting_servers_returns_404(client, kubernetes_client_empty):
    NON_EXISTING_SERVER_NAME = "non-existing"
    response = client.delete(
        f"/service/servers/{NON_EXISTING_SERVER_NAME}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 404


def test_getting_status_for_nonexisting_notebooks_returns_404(
    client, kubernetes_client_empty
):
    headers = AUTHORIZED_HEADERS.copy()
    headers.update({"Accept": "text/plain"})
    response = client.get(f"/service/logs/{SERVER_NAME}", headers=headers)
    assert response.status_code == 404


def test_image_does_not_exist(client, kubernetes_client_empty):
    payload = {
        "namespace": "does_not_exist",
        "project": "does_not_exist",
        "commit_sha": "999999",
    }
    response = client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert response.status_code == 404


@patch("renku_notebooks.api.notebooks.create_named_server")
@patch("renku_notebooks.api.notebooks.config")
@patch("renku_notebooks.api.notebooks.image_exists")
@patch("renku_notebooks.api.notebooks.get_docker_token")
def test_image_check_logic_default_fallback(
    get_docker_token,
    image_exists,
    config,
    create_named_server,
    client,
    kubernetes_client_empty,
):
    payload = {**DEFAULT_PAYLOAD, "commit_sha": "345314r3f13415413"}
    image_exists.return_value = False
    get_docker_token.return_value = "token", False
    config.DEFAULT_IMAGE = "default_image"
    create_named_server_response = MagicMock()
    create_named_server_response.status_code = 202
    create_named_server_response.headers = {"Content-Type": "application/json"}
    create_named_server.return_value = create_named_server_response
    client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert create_named_server.call_args[0][-1].get("image") == "default_image"
    assert create_named_server.call_args[0][-1].get("image_pull_secrets") is None


@patch("renku_notebooks.api.notebooks.create_named_server")
@patch("renku_notebooks.api.notebooks.image_exists")
@patch("renku_notebooks.api.notebooks.get_docker_token")
def test_image_check_logic_specific_found(
    get_docker_token, image_exists, create_named_server, client,
):
    requested_image = "hostname.com/image/subimage:tag"
    image_exists.return_value = True
    get_docker_token.return_value = "token", False
    create_named_server_response = MagicMock()
    create_named_server_response.status_code = 202
    create_named_server_response.headers = {"Content-Type": "application/json"}
    create_named_server.return_value = create_named_server_response
    payload = {**DEFAULT_PAYLOAD, "commit_sha": "commit-1", "image": requested_image}
    client.post(
        "/service/servers", headers=AUTHORIZED_HEADERS, json=payload,
    )
    assert image_exists.called_once_with(
        "hostname.com", "image/subimage", "tag", "token"
    )
    assert create_named_server.call_args[0][-1].get("image") == requested_image
    assert create_named_server.call_args[0][-1].get("image_pull_secrets") is None


@patch("renku_notebooks.api.notebooks.create_named_server")
@patch("renku_notebooks.api.notebooks.image_exists")
@patch("renku_notebooks.api.notebooks.get_docker_token")
def test_image_check_logic_specific_not_found(
    get_docker_token, image_exists, create_named_server, client
):
    requested_image = "hostname.com/image/subimage:tag"
    image_exists.return_value = False
    get_docker_token.return_value = None, None
    client.post(
        "/service/servers",
        headers=AUTHORIZED_HEADERS,
        json={**DEFAULT_PAYLOAD, "image": requested_image},
    )
    assert image_exists.called_once_with(
        "hostname.com", "image/subimage", "tag", "token"
    )
    assert not create_named_server.called


@patch("renku_notebooks.api.notebooks.get_renku_project")
@patch("renku_notebooks.api.notebooks.create_named_server")
@patch("renku_notebooks.api.notebooks.config")
@patch("renku_notebooks.api.notebooks.image_exists")
@patch("renku_notebooks.api.notebooks.get_docker_token")
def test_image_check_logic_commit_sha(
    get_docker_token,
    image_exists,
    config,
    create_named_server,
    get_renku_project,
    client,
    kubernetes_client_empty,
):
    payload = {**DEFAULT_PAYLOAD, "commit_sha": "5ds4af4adsf6asf4564"}
    image_exists.return_value = True
    get_docker_token.return_value = "token", True
    config.IMAGE_REGISTRY = "image.registry"
    config.GITLAB_URL = "https://gitlab.com"
    renku_project = MagicMock()
    renku_project.path_with_namespace = payload["namespace"] + "/" + payload["project"]
    create_named_server_response = MagicMock()
    create_named_server_response.status_code = 202
    create_named_server_response.headers = {"Content-Type": "application/json"}
    create_named_server.return_value = create_named_server_response
    get_renku_project.return_value = renku_project
    client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert image_exists.called_once_with(
        "image.registry",
        payload["namespace"] + "/" + payload["project"],
        payload["commit_sha"][:7],
        "token",
    )
    create_named_server.assert_called_once()
    assert create_named_server.call_args[0][-1].get("image") == "/".join(
        [
            "image.registry",
            payload["namespace"],
            payload["project"] + ":" + payload["commit_sha"][:7],
        ]
    )
    assert create_named_server.call_args[0][-1].get("image_pull_secrets") is not None
