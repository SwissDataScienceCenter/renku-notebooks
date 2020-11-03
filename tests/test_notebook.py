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
import pytest
from gitlab import DEVELOPER_ACCESS

from renku_notebooks.util.jupyterhub_ import make_server_name
from renku_notebooks.util.gitlab_ import get_notebook_image, get_renku_project


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
    return client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)


def create_notebook_with_default_parameters(client, **kwargs):
    return create_notebook(
        client,
        **DEFAULT_PAYLOAD,
        **kwargs,
    )


def test_can_check_health(client):
    response = client.get("/health")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "gitlab",
    [
        (
            DEVELOPER_ACCESS,
            {"namespace": "dummynamespace", "project_name": "dummyproject"},
        ),
        (
            DEVELOPER_ACCESS,
            {"namespace": "DummyNamespace", "project_name": "DummyProject"},
        ),
    ],
    indirect=True,
)
def test_can_find_correct_image(client, gitlab):
    from renku_notebooks.wsgi import app

    response = client.get("/service/user", headers=AUTHORIZED_HEADERS)
    user = response.json

    payload = DEFAULT_PAYLOAD.copy()
    payload["namespace"] = gitlab.namespace
    payload["project"] = gitlab.project_name
    app.config["IMAGE_REGISTRY"] = "registry"

    with app.test_request_context(
        "/service/servers", data=payload, headers=AUTHORIZED_HEADERS
    ):
        project = get_renku_project(user, gitlab.namespace, gitlab.project_name)
        image = get_notebook_image(project, None, "0123456")
    assert image == "registry/dummynamespace/dummyproject:0123456"


def test_can_create_notebooks(client, kubernetes_client):
    response = create_notebook_with_default_parameters(client)
    assert response.status_code == 200 or response.status_code == 201


def test_can_get_created_notebooks(client, kubernetes_client):
    create_notebook_with_default_parameters(client)

    response = client.get("/service/servers", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert SERVER_NAME in response.json.get("servers")


def test_can_get_server_status_for_created_notebooks(client, kubernetes_client):
    create_notebook_with_default_parameters(client)

    response = client.get(f"/service/servers/{SERVER_NAME}", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json.get("name") == SERVER_NAME


def test_getting_notebooks_returns_nothing_when_no_notebook_is_created(client):
    response = client.get("/service/servers", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json.get("servers") == {}


def test_can_get_pods_logs(client, kubernetes_client):
    create_notebook_with_default_parameters(client)

    headers = AUTHORIZED_HEADERS.copy()
    response = client.get(f"/service/logs/{SERVER_NAME}", headers=headers)
    assert response.status_code == 200


def test_can_delete_created_notebooks(client, kubernetes_client):
    create_notebook_with_default_parameters(client)

    response = client.delete(
        f"/service/servers/{SERVER_NAME}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 204


def test_can_force_delete_created_notebooks(client, kubernetes_client):
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


def test_recreating_notebooks_return_current_server(client, kubernetes_client):
    create_notebook_with_default_parameters(client)

    response = create_notebook_with_default_parameters(client)
    assert response.status_code == 200
    assert SERVER_NAME in response.json.get("name")


def test_can_create_notebooks_on_different_branches(client, kubernetes_client):
    create_notebook_with_default_parameters(client, branch="branch")

    response = create_notebook_with_default_parameters(client, branch="another-branch")
    assert response.status_code == 201


@pytest.mark.parametrize(
    "payload",
    [
        {"project": "dummyproject", "commit_sha": "0123456789"},
        {"namespace": "dummynamespace", "commit_sha": "0123456789"},
        {"namespace": "dummynamespace", "project": "dummyproject"},
    ],
)
def test_creating_servers_with_incomplete_data_returns_400(
    client, kubernetes_client, payload
):
    response = create_notebook(client, **payload)
    assert response.status_code == 400


def test_can_get_server_options(client):
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
def test_users_with_no_developer_access_can_create_notebooks(client, gitlab):
    response = create_notebook_with_default_parameters(client)
    assert response.status_code == 201


def test_getting_logs_for_nonexisting_notebook_returns_404(client):
    response = client.get("/service/logs/non-existing-hash", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 404


def test_using_extra_slashes_in_notebook_url_results_in_308(client):
    SERVER_URL_WITH_EXTRA_SLASHES = f"/{SERVER_NAME}"
    response = client.post(
        f"/service/servers/{SERVER_URL_WITH_EXTRA_SLASHES}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 308


def test_deleting_nonexisting_servers_returns_404(client):
    NON_EXISTING_SERVER_NAME = "non-existing"
    response = client.delete(
        f"/service/servers/{NON_EXISTING_SERVER_NAME}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 404


def test_getting_status_for_nonexisting_notebooks_returns_404(client):
    headers = AUTHORIZED_HEADERS.copy()
    headers.update({"Accept": "text/plain"})
    response = client.get(f"/service/logs/{SERVER_NAME}", headers=headers)
    assert response.status_code == 404
