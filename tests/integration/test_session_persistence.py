# -*- coding: utf-8 -*-
#
# Copyright 2021 - Swiss Data Science Center (SDSC)
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
"""Tests for hibernating sessions."""

import requests


def test_listing_hibernated_sessions(
    base_url,
    gitlab_client,
    gitlab_project,
    headers,
    is_gitlab_client_anonymous,
    start_session_and_wait_until_ready,
    valid_payload,
):
    """Test getting required data from hibernated sessions."""
    if is_gitlab_client_anonymous(gitlab_client):
        # NOTE: Anonymous users don't have any persisted sessions
        return

    session = start_session_and_wait_until_ready(headers, valid_payload, gitlab_project)
    assert session is not None

    server_name = session.json()["name"]
    server_url = f"{base_url}/servers/{server_name}"
    response = requests.patch(server_url, json={"state": "hibernated"}, headers=headers)
    assert response.status_code == 204, response.text

    # NOTE: Get all servers
    response = requests.get(f"{base_url}/servers", headers=headers)
    assert response.status_code == 200
    servers = response.json().get("servers", {})

    # NOTE: All these checks are for registered users
    assert server_name in servers

    # NOTE: Get a single server
    response = requests.get(server_url, headers=headers)

    assert response.status_code == 200
    server = response.json()
    assert server["name"] == server_name
    annotations = server["annotations"]
    assert annotations["renku.io/hibernation"]
    assert annotations["renku.io/hibernation-branch"] == "master"
    commit = gitlab_project.commits.get("HEAD")
    assert annotations["renku.io/hibernation-commit-sha"] == commit.id
    assert annotations["renku.io/hibernation-dirty"] == "false"
    assert annotations["renku.io/hibernation-synchronized"] == "true"
    assert annotations["renku.io/hibernation-date"]
    assert int(annotations["renku.io/hibernatedSecondsThreshold"]) > 0


def test_hibernating_anonymous_users_sessions(
    base_url,
    gitlab_client,
    gitlab_project,
    headers,
    is_gitlab_client_anonymous,
    start_session_and_wait_until_ready,
    valid_payload,
):
    """Test that hibernating anonymous users' sessions isn't allowed."""
    if not is_gitlab_client_anonymous(gitlab_client):
        return

    session = start_session_and_wait_until_ready(headers, valid_payload, gitlab_project)
    assert session is not None

    server_name = session.json()["name"]
    server_url = f"{base_url}/servers/{server_name}"
    response = requests.patch(server_url, json={"state": "hibernated"}, headers=headers)

    assert response.status_code == 422, response.text
