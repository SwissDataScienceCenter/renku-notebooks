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


def test_autosaves_branches(
    gitlab_client, create_branch, gitlab_project, headers, base_url
):
    non_autosave_branch_names = [
        "branch1",
        "branch2",
    ]
    commit = gitlab_project.commits.get("HEAD")
    [create_branch(i) for i in non_autosave_branch_names]
    autosave_branch = create_branch(
        f"renku/autosave/{gitlab_client.user.username}/branch2/{commit.id[:7]}/{commit.id[:7]}"
    )
    response = requests.get(
        f"{base_url}/{quote_plus(gitlab_project.path_with_namespace)}/autosave",
        headers=headers,
    )
    assert response.status_code == 200
    returned_autosave = response.json()["autosaves"][0]
    returned_autosave["date"] = datetime.fromisoformat(returned_autosave["date"])
    assert returned_autosave == {
        "branch": "branch2",
        "commit": commit.id,
        "date": datetime.fromisoformat(autosave_branch.commit["committed_date"]),
        "pvs": False,
        "name": f"renku/autosave/{gitlab_client.user.username}"
        f"/branch2/{commit.id[:7]}/{commit.id[:7]}",
    }


def test_autosaves_non_existing_project(base_url, headers):
    namespace_project = "wrong_namespace/wrong_project"
    response = requests.get(
        f"{base_url}/{quote_plus(namespace_project)}/autosaves", headers=headers
    )
    assert response.status_code == 404
