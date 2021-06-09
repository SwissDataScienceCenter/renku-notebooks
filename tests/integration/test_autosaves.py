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
from unittest.mock import patch
from urllib.parse import quote_plus


def test_autosaves_branches(setup_project, client, proper_headers):
    tstamp = datetime(2020, 1, 1, 1)
    namespace = "namespace"
    project = "project"
    namespace_project = f"{namespace}/{project}"
    setup_project(
        namespace_project,
        [
            "master",
            "branch1",
            f"renku/autosave/{namespace}/branch2/1111111/2222222",
            "branch2",
        ],
        ["123243534", "425236526542", "9999999", "1111111", "2222222"],
        tstamp.isoformat(),
    )
    response = client.get(
        f"/notebooks/{quote_plus(namespace_project)}/autosave", headers=proper_headers
    )
    assert response.status_code == 200
    assert response.json == {
        "autosaves": [
            {
                "branch": "branch2",
                "commit": "1111111",
                "date": tstamp.isoformat(),
                "pvs": False,
                "name": f"renku/autosave/{namespace}/branch2/1111111/2222222",
            },
        ],
        "pvsSupport": False,
    }


@patch("renku_notebooks.api.classes.user.User.get_renku_project")
def test_autosaves_non_existing_project(get_renku_project, client, proper_headers):
    get_renku_project.return_value = None
    namespace_project = "wrong_namespace/wrong_project"
    response = client.get(
        f"/notebooks/{quote_plus(namespace_project)}/autosave", headers=proper_headers
    )
    assert response.status_code == 404
