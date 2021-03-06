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
from unittest.mock import patch
import json
import os

from renku_notebooks.api.classes.server import UserServer


AUTHORIZED_HEADERS = {"Authorization": "token 8f7e09b3bf6b8a20"}
SERVER_NAME = UserServer.make_server_name(
    "dummynamespace", "dummyproject", "master", "0123456789"
)
NON_DEVELOPER_ACCESS = DEVELOPER_ACCESS - 1
DEFAULT_PAYLOAD = {
    "namespace": "dummynamespace",
    "project": "dummyproject",
    "commit_sha": "0123456789",
    "serverOptions": {
        "cpu_request": 0.1,
        "defaultUrl": "/lab",
        "lfs_auto_fetch": True,
        "mem_request": "1G",
    },
}


def create_notebook(client, **payload):
    response = client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    return response


def create_notebook_with_default_parameters(client, **kwargs):
    return create_notebook(client, **DEFAULT_PAYLOAD, **kwargs)


def test_can_check_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_can_create_notebooks(
    client,
    make_all_images_valid,
    make_server_args_valid,
    kubernetes_client,
    pod_items,
    mock_server_start,
):
    response = create_notebook_with_default_parameters(client)
    assert response.status_code == 202 or response.status_code == 201


def test_can_get_created_notebooks(
    client, kubernetes_client, make_all_images_valid, mock_server_start
):
    create_notebook_with_default_parameters(client)

    response = client.get("/service/servers", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert SERVER_NAME in response.json.get("servers")


def test_can_get_server_status_for_created_notebooks(
    client,
    kubernetes_client,
    make_all_images_valid,
    make_server_args_valid,
    mock_server_start,
):
    create_notebook_with_default_parameters(client)

    response = client.get(f"/service/servers/{SERVER_NAME}", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json.get("name") == SERVER_NAME


def test_getting_notebooks_returns_nothing_when_no_notebook_is_created(
    client, kubernetes_client
):
    response = client.get("/service/servers", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json.get("servers") == {}


def test_can_get_pods_logs(
    client, kubernetes_client, make_all_images_valid, mock_server_start
):
    create_notebook_with_default_parameters(client)

    headers = AUTHORIZED_HEADERS.copy()
    response = client.get(f"/service/logs/{SERVER_NAME}", headers=headers)
    assert response.status_code == 200


def test_can_delete_created_notebooks(
    client, kubernetes_client, make_all_images_valid, mock_server_start
):
    create_notebook_with_default_parameters(client)

    response = client.delete(
        f"/service/servers/{SERVER_NAME}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 204


def test_can_force_delete_created_notebooks(
    client, kubernetes_client, make_all_images_valid, mock_server_start
):
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
    client,
    kubernetes_client,
    make_all_images_valid,
    make_server_args_valid,
    mock_server_start,
):
    response = create_notebook_with_default_parameters(client)
    response = create_notebook_with_default_parameters(client)
    assert response.status_code == 200
    assert SERVER_NAME in response.json.get("name")


def test_can_create_notebooks_on_different_branches(
    client,
    kubernetes_client,
    make_all_images_valid,
    make_server_args_valid,
    mock_server_start,
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
def test_creating_servers_with_incomplete_data_returns_422(
    client, kubernetes_client, payload
):
    response = create_notebook(client, **payload)
    assert response.status_code == 422


def test_can_get_server_options(client, kubernetes_client):
    response = client.get("/service/server_options", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json == json.load(open("tests/dummy_server_options.json", "r"))


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
    client, gitlab, make_all_images_valid, kubernetes_client, mock_server_start
):
    response = create_notebook(
        client, **{**DEFAULT_PAYLOAD, "commit_sha": "5648434fds89"}
    )
    assert response.status_code == 202 or response.status_code == 201


def test_launching_notebook_with_invalid_server_options(
    client, gitlab, make_all_images_valid, kubernetes_client, mock_server_start
):
    response = create_notebook(
        client,
        **{
            **DEFAULT_PAYLOAD,
            "serverOptions": {
                "cpu_request": 20,
                "defaultUrl": "some_url",
                "gpu_request": 20,
                "lfs_auto_fetch": True,
                "mem_request": "100G",
            },
        },
    )
    assert response.status_code == 422


def test_getting_logs_for_nonexisting_notebook_returns_404(client, kubernetes_client):
    response = client.get("/service/logs/non-existing-hash", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 404


def test_using_extra_slashes_in_notebook_url_results_in_308(client, kubernetes_client):
    SERVER_URL_WITH_EXTRA_SLASHES = f"/{SERVER_NAME}"
    response = client.post(
        f"/service/servers/{SERVER_URL_WITH_EXTRA_SLASHES}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 308


def test_deleting_nonexisting_servers_returns_404(client, kubernetes_client):
    NON_EXISTING_SERVER_NAME = "non-existing"
    response = client.delete(
        f"/service/servers/{NON_EXISTING_SERVER_NAME}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 404


def test_getting_status_for_nonexisting_notebooks_returns_404(
    client, kubernetes_client
):
    headers = AUTHORIZED_HEADERS.copy()
    headers.update({"Accept": "text/plain"})
    response = client.get(f"/service/logs/{SERVER_NAME}", headers=headers)
    assert response.status_code == 404


@patch("renku_notebooks.api.classes.server.UserServer._branch_exists")
@patch("renku_notebooks.api.classes.server.UserServer._commit_sha_exists")
@patch("renku_notebooks.api.classes.server.UserServer._project_exists")
def test_project_does_not_exist(
    _project_exists,
    _commit_sha_exists,
    _branch_exists,
    client,
    make_all_images_valid,
    kubernetes_client,
):
    _project_exists.return_value = False
    _commit_sha_exists.return_value = True
    _branch_exists.return_value = True
    payload = {
        "namespace": "does_not_exist",
        "project": "does_not_exist",
        "commit_sha": "999999",
    }
    response = client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert response.status_code == 404


@patch("renku_notebooks.api.classes.server.requests", autospec=True)
@patch("renku_notebooks.api.classes.server.image_exists")
@patch("renku_notebooks.api.classes.server.get_docker_token")
def test_image_check_logic_default_fallback(
    get_docker_token,
    image_exists,
    mock_requests,
    client,
    make_server_args_valid,
    kubernetes_client,
):
    payload = {**DEFAULT_PAYLOAD}
    image_exists.return_value = False
    get_docker_token.return_value = "token", False
    client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert (
        mock_requests.post.call_args[-1].get("json", {}).get("image")
        == os.environ["DEFAULT_IMAGE"]
    )
    assert (
        mock_requests.post.call_args[-1].get("json", {}).get("image_pull_secrets")
        is None
    )


@patch("renku_notebooks.api.classes.server.requests", autospec=True)
@patch("renku_notebooks.api.classes.server.image_exists")
@patch("renku_notebooks.api.classes.server.get_docker_token")
def test_image_check_logic_specific_found(
    get_docker_token,
    image_exists,
    mock_requests,
    client,
    make_server_args_valid,
    kubernetes_client,
):
    requested_image = "hostname.com/image/subimage:tag"
    image_exists.return_value = True
    get_docker_token.return_value = "token", False
    payload = {**DEFAULT_PAYLOAD, "commit_sha": "commit-1", "image": requested_image}
    client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert image_exists.called_once_with(
        "hostname.com", "image/subimage", "tag", "token"
    )
    assert (
        mock_requests.post.call_args[-1].get("json", {}).get("image") == requested_image
    )
    assert (
        mock_requests.post.call_args[-1].get("json", {}).get("image_pull_secrets")
        is None
    )


@patch("renku_notebooks.api.classes.server.requests", autospec=True)
@patch("renku_notebooks.api.classes.server.image_exists")
@patch("renku_notebooks.api.classes.server.get_docker_token")
def test_image_check_logic_specific_not_found(
    get_docker_token, image_exists, mock_requests, client, make_server_args_valid
):
    requested_image = "hostname.com/image/subimage:tag"
    image_exists.return_value = False
    get_docker_token.return_value = None, None
    client.post(
        "/service/servers",
        headers=AUTHORIZED_HEADERS,
        json={**DEFAULT_PAYLOAD, "image": requested_image},
    )
    assert not mock_requests.post.called


@patch("renku_notebooks.api.classes.server.UserServer._create_registry_secret")
@patch("renku_notebooks.api.classes.server.requests", autospec=True)
@patch("renku_notebooks.api.classes.server.image_exists")
@patch("renku_notebooks.api.classes.server.get_docker_token")
def test_image_check_logic_commit_sha(
    get_docker_token,
    image_exists,
    mock_requests,
    create_reg_secret_mock,
    client,
    make_server_args_valid,
    kubernetes_client,
):
    payload = {**DEFAULT_PAYLOAD, "commit_sha": "5ds4af4adsf6asf4564"}
    image_exists.return_value = True
    get_docker_token.return_value = "token", True
    client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert create_reg_secret_mock.called_once
    assert image_exists.called_once_with(
        os.environ["IMAGE_REGISTRY"],
        payload["namespace"] + "/" + payload["project"],
        payload["commit_sha"][:7],
        "token",
    )
    assert mock_requests.post.call_args[-1].get("json", {}).get("image") == "/".join(
        [
            os.environ["IMAGE_REGISTRY"],
            payload["namespace"],
            payload["project"] + ":" + payload["commit_sha"][:7],
        ]
    )
    assert (
        mock_requests.post.call_args[-1].get("json", {}).get("image_pull_secrets")
        is not None
    )
