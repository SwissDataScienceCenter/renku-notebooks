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
"""Tests for Autosaves of the Notebook Services API"""
from datetime import datetime
from urllib.parse import quote_plus
import requests


def test_autosaves_listing(
    registered_gitlab_client,
    create_remote_branch,
    gitlab_project,
    headers,
    base_url,
    gitlab_client,
    is_gitlab_client_anonymous,
):
    non_autosave_branch_names = [
        "branch1",
        "branch2",
    ]
    commit = gitlab_project.commits.get("HEAD")
    [create_remote_branch(i) for i in non_autosave_branch_names]
    autosave_branch = create_remote_branch(
        f"renku/autosave/{registered_gitlab_client.user.username}/branch2/"
        f"{commit.id[:7]}/{commit.id[:7]}"
    )
    response = requests.get(
        f"{base_url}/{quote_plus(gitlab_project.path_with_namespace)}/autosave",
        headers=headers,
    )
    assert response.status_code == 200
    if is_gitlab_client_anonymous(gitlab_client):
        assert len(response.json()["autosaves"]) == 0
    else:
        returned_autosave = response.json()["autosaves"][0]
        returned_autosave["date"] = datetime.fromisoformat(returned_autosave["date"])
        assert returned_autosave == {
            "branch": "branch2",
            "commit": commit.id[:7],
            "date": datetime.fromisoformat(autosave_branch.commit["committed_date"]),
            "pvs": False,
            "name": f"renku/autosave/{registered_gitlab_client.user.username}"
            f"/branch2/{commit.id[:7]}/{commit.id[:7]}",
        }


def test_autosaves_non_existing_project(base_url, headers):
    namespace_project = "wrong_namespace/wrong_project"
    response = requests.get(
        f"{base_url}/{quote_plus(namespace_project)}/autosaves", headers=headers
    )
    assert response.status_code == 404


def test_autosave_is_created_and_restored(
    launch_session,
    delete_session,
    valid_payload,
    base_url,
    headers,
    gitlab_project,
    pod_exec,
    k8s_namespace,
):
    response = launch_session(valid_payload, gitlab_project, headers)
    assert response is not None and response.status_code == 201
    server_name = response.json()["name"]
    unsaved_file = ".test-file-1"
    unsaved_content = "test-content"
    container_name = "jupyter-server"
    files_in_repo = pod_exec(
        k8s_namespace,
        server_name,
        container_name,
        "ls -la"
    )
    # INFO: Ensure that the initial session that is launched is not empty
    assert "Dockerfile" in files_in_repo
    assert ".renku" in files_in_repo
    session_commit = pod_exec(
        k8s_namespace,
        server_name,
        container_name,
        "git rev-parse HEAD",
    )
    assert session_commit.strip() == valid_payload["commit_sha"]
    pod_exec(
        k8s_namespace,
        server_name,
        container_name,
        f"sh -c 'echo \"{unsaved_content}\" > {unsaved_file}'"
    )
    delete_session(response.json(), gitlab_project, headers)
    autosaves_response = requests.get(
        f"{base_url}/{quote_plus(gitlab_project.path_with_namespace)}/autosave",
        headers=headers,
    )
    assert autosaves_response.status_code == 200
    autosaves = autosaves_response.json()
    assert len(autosaves.get("autosaves", [])) == 1
    # INFO: Now launch session and confirm autosave is recovered
    response = launch_session(valid_payload, gitlab_project, headers)
    assert response is not None and response.status_code == 201
    files_in_repo = pod_exec(
        k8s_namespace,
        server_name,
        container_name,
        "ls -la"
    )
    assert unsaved_file in files_in_repo
    # INFO: Ensurre the autosave has been deleted after recovery
    autosaves_response = requests.get(
        f"{base_url}/{quote_plus(gitlab_project.path_with_namespace)}/autosave",
        headers=headers,
    )
    assert autosaves_response.status_code == 200
    autosaves = autosaves_response.json()
    assert len(autosaves.get("autosaves", ["something"])) == 0
    delete_session(response.json(), gitlab_project, headers)
