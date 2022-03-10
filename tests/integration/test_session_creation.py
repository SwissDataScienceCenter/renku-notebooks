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

import os

import pytest
import requests
import semver


def test_can_check_health():
    response = requests.get(os.environ["NOTEBOOKS_BASE_URL"] + "/health")
    assert response.status_code == 200


def test_version_endpoint(base_url):
    response = requests.get(f"{base_url}/version")

    assert response.status_code == 200
    assert response.json()["name"] == "renku-notebooks"

    versions = response.json()["versions"]
    assert isinstance(versions, list)

    version = versions[0]["version"]
    assert version != "0.0.0"
    assert semver.VersionInfo.isvalid(version)

    data = versions[0]["data"]
    assert type(data.get("anonymousSessionsEnabled")) is bool
    storage = data.get("cloudstorageEnabled", {})
    assert type(storage.get("s3")) is bool


def test_getting_session_and_logs_after_creation(
    headers, launch_session, delete_session, base_url, valid_payload, gitlab_project
):
    session = launch_session(valid_payload, gitlab_project, headers).json()
    assert session is not None
    server_name = session["name"]
    response = requests.get(f"{base_url}/servers", headers=headers)
    assert response.status_code == 200
    assert session["name"] in response.json().get("servers", {})
    response = requests.get(f"{base_url}/servers/{server_name}", headers=headers)
    assert response.status_code == 200
    assert response.json().get("name") == server_name
    response = requests.get(f"{base_url}/logs/{server_name}", headers=headers)
    assert response.status_code == 200
    delete_session(session, gitlab_project, headers)


def test_getting_notebooks_returns_nothing_when_no_notebook_is_active(
    base_url, headers
):
    response = requests.get(f"{base_url}/servers", headers=headers)
    assert response.status_code == 200
    assert response.json().get("servers") == {}


@pytest.mark.parametrize("query_string", [{}, {"force": "true"}])
def test_can_delete_created_notebooks(
    query_string,
    headers,
    launch_session,
    delete_session,
    base_url,
    valid_payload,
    gitlab_project,
):
    session = launch_session(valid_payload, gitlab_project, headers).json()
    assert session is not None
    server_name = session["name"]
    response = requests.delete(
        f"{base_url}/servers/{server_name}", headers=headers, params=query_string
    )
    assert response.status_code == 204
    response = requests.get(f"{base_url}/servers/{server_name}", headers=headers)
    assert response.status_code == 200
    assert not response.json().get("status").get("ready")
    delete_session(session, gitlab_project, headers)


def test_recreating_notebooks_returns_current_server(
    headers, launch_session, delete_session, base_url, valid_payload, gitlab_project
):
    response1 = launch_session(valid_payload, gitlab_project, headers)
    assert response1 is not None and response1.status_code == 201
    response2 = launch_session(valid_payload, gitlab_project, headers)
    assert response2 is not None and response2.status_code == 200
    server_name1 = response1.json()["name"]
    server_name2 = response2.json()["name"]
    assert server_name1 == server_name2
    response = requests.get(f"{base_url}/servers/{server_name1}", headers=headers)
    assert response.status_code == 200
    delete_session(response1.json(), gitlab_project, headers)


def test_can_create_notebooks_on_different_branches(
    create_remote_branch,
    launch_session,
    delete_session,
    valid_payload,
    base_url,
    headers,
    gitlab_project,
):
    branch1_name = "different-branch1"
    branch2_name = "different-branch2"
    create_remote_branch(branch1_name)
    create_remote_branch(branch2_name)
    response1 = launch_session(
        {**valid_payload, "branch": branch1_name}, gitlab_project, headers
    )
    response2 = launch_session(
        {**valid_payload, "branch": branch2_name}, gitlab_project, headers
    )
    assert response1 is not None and response1.status_code == 201
    assert response2 is not None and response2.status_code == 201
    server_name1 = response1.json()["name"]
    server_name2 = response2.json()["name"]
    assert server_name1 != server_name2
    assert (
        requests.get(f"{base_url}/servers/{server_name1}", headers=headers).status_code
        == 200
    )
    assert (
        requests.get(f"{base_url}/servers/{server_name2}", headers=headers).status_code
        == 200
    )
    delete_session(response1.json(), gitlab_project, headers)
    delete_session(response2.json(), gitlab_project, headers)


@pytest.fixture(
    # missing parameter names
    params=["commit_sha", "namespace", "project"]
)
def incomplete_payload(request, valid_payload):
    output = {**valid_payload}
    output.pop(request.param)
    return output


def test_creating_servers_with_incomplete_data_returns_422(
    launch_session, incomplete_payload, gitlab_project, headers
):
    response = launch_session(incomplete_payload, gitlab_project, headers)
    assert response is not None and response.status_code == 422


def test_can_get_server_options(base_url, headers, server_options_ui):
    response = requests.get(f"{base_url}/server_options", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        **server_options_ui,
        # NOTE: enable when the UI fully supports s3
        # currently this breaks the session settings page
        # "cloudstorage": {
        #     "s3": {"enabled": os.getenv("S3_MOUNTS_ENABLED", "false") == "true"}
        # },
    }


def test_using_extra_slashes_in_notebook_url(
    base_url, headers, launch_session, delete_session, valid_payload, gitlab_project
):
    response = launch_session(valid_payload, gitlab_project, headers)
    assert response is not None and response.status_code == 201
    server_name = response.json()["name"]
    response = requests.get(f"{base_url}/servers//{server_name}", headers=headers)
    assert response.status_code == 200
    delete_session(response.json(), gitlab_project, headers)
