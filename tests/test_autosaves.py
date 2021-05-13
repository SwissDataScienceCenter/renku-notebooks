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
import pytest
from kubernetes.client import V1PersistentVolumeClaim, V1ObjectMeta
from unittest.mock import patch

from renku_notebooks.api import config
from renku_notebooks.util.kubernetes_ import make_server_name
from tests.conftest import _AttributeDictionary, CustomList

AUTHORIZED_HEADERS = {"Authorization": "token 8f7e09b3bf6b8a20"}


def dict_from_object(obj):
    # taken from code for config.from_object in flask
    output = {}
    for key in dir(obj):
        if key.isupper():
            output[key] = getattr(obj, key)
    return output


@pytest.fixture
def setup_pvcs(mocker):
    def _setup_pvcs(project, branches, commits, commited_datetime):
        mocker.patch("renku_notebooks.api.classes.user.User._get_pvcs").return_value = [
            V1PersistentVolumeClaim(
                metadata=V1ObjectMeta(
                    name=make_server_name("dummyuser", project, branches[i], commits[i])
                    + "-pvc",
                    annotations={
                        config.RENKU_ANNOTATION_PREFIX + "projectName": project,
                        config.RENKU_ANNOTATION_PREFIX + "namespace": "dummyuser",
                        config.RENKU_ANNOTATION_PREFIX + "branch": branches[i],
                        config.RENKU_ANNOTATION_PREFIX + "commit-sha": commits[i],
                    },
                    creation_timestamp=commited_datetime,
                ),
            )
            for i in range(len(branches))
        ]

    yield _setup_pvcs


@pytest.fixture
def setup_project(mocker):
    def _setup_project(branches, commits, date_isostring):
        mocker.patch(
            "renku_notebooks.api.classes.user.User.get_renku_project"
        ).return_value = _AttributeDictionary(
            {
                "name": "project_name",
                "commits": _AttributeDictionary(
                    {commit: _AttributeDictionary({"id": commit}) for commit in commits}
                ),
                "branches": CustomList(
                    *[
                        _AttributeDictionary(
                            {
                                "name": branch,
                                "commit": _AttributeDictionary(
                                    {"committed_date": date_isostring}
                                ),
                            }
                        )
                        for branch in branches
                    ],
                ),
            }
        )

    yield _setup_project


@pytest.fixture
def patch_config(mocker):
    def _patch_config(props_to_override):
        mock_config = _AttributeDictionary(
            {**dict_from_object(config), **props_to_override}
        )
        mocker.patch(
            "renku_notebooks.api.classes.user.current_app"
        ).config = mock_config
        mocker.patch("renku_notebooks.api.notebooks.current_app").config = mock_config
        mocker.patch(
            "renku_notebooks.api.classes.storage.current_app"
        ).config = mock_config

    yield _patch_config


def test_autosaves_only_pvs(setup_pvcs, setup_project, patch_config, client):
    tstamp = datetime(2020, 1, 1, 1)
    patch_config({"NOTEBOOKS_SESSION_PVS_ENABLED": True})
    setup_project(
        ["master", "branch1"],
        ["123243534", "425236526542", "1235435"],
        tstamp.isoformat(),
    )
    setup_pvcs("project", ["branch1"], ["1235435"], tstamp)
    response = client.get(
        "/service/autosave/namespace/project", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 200
    assert response.json == {
        "autosaves": [
            {
                "branch": "branch1",
                "commit": "1235435",
                "date": tstamp.isoformat(),
                "pvs": True,
                "name": make_server_name("dummyuser", "project", "branch1", "1235435")
                + "-pvc",
            }
        ],
        "pvsSupport": True,
    }


def test_autosaves_branches_pvs(setup_pvcs, setup_project, patch_config, client):
    tstamp = datetime(2020, 1, 1, 1)
    patch_config({"NOTEBOOKS_SESSION_PVS_ENABLED": True})
    setup_project(
        [
            "master",
            "branch1",
            "branch2",
            "renku/autosave/dummyuser/branch2/1111111/2222222",
        ],
        ["123243534", "425236526542", "9999999", "1111111", "2222222", "1235435"],
        tstamp.isoformat(),
    )
    setup_pvcs("project", ["branch1"], ["1235435"], tstamp)
    response = client.get(
        "/service/autosave/namespace/project", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 200
    assert response.json == {
        "autosaves": [
            {
                "branch": "branch1",
                "commit": "1235435",
                "date": tstamp.isoformat(),
                "pvs": True,
                "name": make_server_name("dummyuser", "project", "branch1", "1235435")
                + "-pvc",
            },
            {
                "branch": "branch2",
                "commit": "1111111",
                "date": tstamp.isoformat(),
                "pvs": False,
                "name": "renku/autosave/dummyuser/branch2/1111111/2222222",
            },
        ],
        "pvsSupport": True,
    }


def test_autosaves_only_branches(setup_pvcs, setup_project, patch_config, client):
    tstamp = datetime(2020, 1, 1, 1)
    patch_config({"NOTEBOOKS_SESSION_PVS_ENABLED": False})
    setup_project(
        [
            "master",
            "branch1",
            "renku/autosave/dummyuser/branch2/1111111/2222222",
            "branch2",
        ],
        ["123243534", "425236526542", "9999999", "1111111", "2222222"],
        tstamp.isoformat(),
    )
    setup_pvcs("project", ["branch1"], ["1235435"], tstamp)
    response = client.get(
        "/service/autosave/namespace/project", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 200
    assert response.json == {
        "autosaves": [
            {
                "branch": "branch2",
                "commit": "1111111",
                "date": tstamp.isoformat(),
                "pvs": False,
                "name": "renku/autosave/dummyuser/branch2/1111111/2222222",
            },
        ],
        "pvsSupport": False,
    }


def test_autosaves_no_pvs(setup_pvcs, setup_project, patch_config, client):
    tstamp = datetime(2020, 1, 1, 1)
    patch_config({"NOTEBOOKS_SESSION_PVS_ENABLED": True})
    setup_project(
        ["master", "branch1"],
        ["123243534", "425236526542", "9999999", "11111111", "22222222"],
        tstamp.isoformat(),
    )
    setup_pvcs("project", [], [], tstamp)
    response = client.get(
        "/service/autosave/namespace/project", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 200
    assert response.json == {
        "autosaves": [],
        "pvsSupport": True,
    }


@patch("renku_notebooks.api.classes.user.User.get_renku_project")
def test_autosaves_non_existing_project(get_renku_project, client):
    get_renku_project.return_value = None
    response = client.get(
        "/service/autosave/namespace/wrong_project", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 404
