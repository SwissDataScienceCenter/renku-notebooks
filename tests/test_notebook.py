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
from hashlib import md5

import pytest
from gitlab import DEVELOPER_ACCESS

AUTHORIZED_HEADERS = {"Authorization": "token 8f7e09b3bf6b8a20"}
PROJECT_URL = "dummynamespace/dummyproject/0123456789"
SERVER_NAME = md5((PROJECT_URL.replace("/", "") + "master").encode()).hexdigest()[:16]
NON_DEVELOPER_ACCESS = DEVELOPER_ACCESS - 1


def test_can_check_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_can_create_notebooks(client):
    response = client.post(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200 or response.status_code == 201


def test_can_get_created_notebooks(client):
    client.post(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)

    response = client.get("/service/servers", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert SERVER_NAME in response.json.get("servers")


def test_can_get_server_status_for_created_notebooks(client, kubernetes_client):
    response = client.post(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)

    response = client.get(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json.get("name") == SERVER_NAME


def test_getting_notebooks_returns_nothing_when_no_notebook_is_created(client):
    response = client.get("/service/servers", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json.get("servers") == {}


def test_can_get_server_options(client):
    client.post(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)

    response = client.get(
        f"/service/{PROJECT_URL}/server_options", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 200
    assert response.json == {"dummy-key": {"default": "dummy-value"}}


def test_can_get_pods_logs(client, kubernetes_client):
    client.post(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)

    headers = AUTHORIZED_HEADERS.copy()
    headers.update({"Accept": "text/plain"})
    response = client.get(f"/service/{PROJECT_URL}/logs", headers=headers)
    assert response.status_code == 200


def test_can_delete_created_notebooks(client):
    client.post(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)

    response = client.delete(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 204


def test_can_delete_created_notebooks_with_server_name(client):
    client.post(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)

    response = client.delete(
        f"/service/servers/{SERVER_NAME}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 204


def test_recreating_notebooks_return_current_server(client, kubernetes_client):
    response = client.post(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)

    response = client.post(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert SERVER_NAME in response.json.get("name")


@pytest.mark.parametrize("gitlab", [NON_DEVELOPER_ACCESS], indirect=True)
def test_users_with_no_developer_access_cannot_create_notebooks(client, gitlab):
    response = client.post(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 401


def test_getting_logs_for_nonexisting_notebook_returns_404(client, kubernetes_client):
    response = client.get(
        f"/service/{PROJECT_URL}/logs",
        headers=AUTHORIZED_HEADERS,
        environ_base={"HTTP_ACCEPT": "text/plain"},
    )
    assert response.status_code == 404


def test_getting_logs_with_json_mime_type_returns_406(client, kubernetes_client):
    response = client.post(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)

    headers = AUTHORIZED_HEADERS.copy()
    headers.update({"Accept": "application/json"})
    response = client.get(f"/service/{PROJECT_URL}/logs", headers=headers)
    assert response.status_code == 406


def test_using_extra_slashes_in_notebook_url_results_in_404(client):
    PROJECT_URL_WITH_EXTRA_SLASHES = f"/{PROJECT_URL}"
    response = client.post(
        f"/service/{PROJECT_URL_WITH_EXTRA_SLASHES}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 404


def test_cannot_delete_nonexisting_servers(client):
    response = client.delete(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 404


@pytest.mark.xfail(strict=True)
def test_getting_status_for_nonexisting_notebooks_returns_404(client):
    response = client.get(f"/service/{PROJECT_URL}", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 404
