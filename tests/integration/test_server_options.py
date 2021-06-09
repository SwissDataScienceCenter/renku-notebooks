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
from copy import deepcopy
from gitlab import DEVELOPER_ACCESS
import pytest
from unittest.mock import patch

from renku_notebooks import config
from renku_notebooks.util.kubernetes_ import make_server_name


AUTHORIZED_HEADERS = {"Authorization": "token 8f7e09b3bf6b8a20"}
SERVER_NAME = make_server_name("dummynamespace", "dummyproject", "master", "0123456789")
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

valid_server_options = [
    # request with server options passed as empty dictionary
    {},
    # request with a few omitted fields
    {"cpu_request": 0.1, "defaultUrl": "/lab", "lfs_auto_fetch": True},
    {"cpu_request": 0.1, "defaultUrl": "/lab", "mem_request": "1G"},
    {"cpu_request": 0.1, "lfs_auto_fetch": True, "mem_request": "1G"},
    {"defaultUrl": "/lab", "lfs_auto_fetch": True, "mem_request": "1G"},
    # ensure that default url is not validated (this is how it should be)
    # since users can add or change the url where the session is available
    {"defaultUrl": "/random", "lfs_auto_fetch": True, "mem_request": "1G"},
    # disk request not in available options but in valid range
    {"defaultUrl": "/random", "lfs_auto_fetch": True, "disk_request": "54G"},
]

invalid_server_options = [
    # request disk size outside of valid range
    {
        "cpu_request": 0.1,
        "defaultUrl": "/lab",
        "lfs_auto_fetch": True,
        "mem_request": "1G",
        "disk_request": "101G",
    },
    {
        "cpu_request": 0.1,
        "defaultUrl": "/lab",
        "lfs_auto_fetch": True,
        "mem_request": "1G",
        "disk_request": "0.5G",
    },
    # only option for gpus is 0, but 4 requested
    {
        "cpu_request": 0.1,
        "defaultUrl": "/lab",
        "lfs_auto_fetch": True,
        "mem_request": "1G",
        "gpu_request": 4,
    },
    # cpu request out of valid range
    {
        "cpu_request": 20,
        "defaultUrl": "/lab",
        "lfs_auto_fetch": True,
        "mem_request": "1G",
        "gpu_request": 0,
    },
    # lfs auto fetch has wrong type
    {
        "cpu_request": 0.1,
        "defaultUrl": "/lab",
        "lfs_auto_fetch": 456,
        "mem_request": "1G",
        "gpu_request": 0,
    },
    # memory request does not equal default value
    # and it has no alternatives specified in server options for UI
    {
        "cpu_request": 0.1,
        "defaultUrl": "/lab",
        "lfs_auto_fetch": True,
        "mem_request": "100G",
        "gpu_request": 0,
    },
]


@pytest.mark.parametrize("server_options", valid_server_options)
def test_can_start_notebook_with_valid_server_options(
    server_options,
    client,
    make_all_images_valid,
    make_server_args_valid,
    mock_server_start,
    kubernetes_client,
):
    payload = {**DEFAULT_PAYLOAD, "serverOptions": server_options}
    response = client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert response.status_code == 202 or response.status_code == 201


@pytest.mark.parametrize("server_options", invalid_server_options)
def test_can_not_start_notebook_with_invalid_options(
    server_options,
    client,
    make_all_images_valid,
    make_server_args_valid,
    mock_server_start,
    kubernetes_client,
):
    payload = {**DEFAULT_PAYLOAD, "serverOptions": server_options}
    response = client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize("test_server_options", valid_server_options)
@patch("renku_notebooks.api.notebooks.UserServer")
def test_proper_defaults_applied_to_server_options(
    server_patch,
    test_server_options,
    client,
    make_all_images_valid,
    make_server_args_valid,
):
    test_payload = {**DEFAULT_PAYLOAD, "serverOptions": test_server_options}
    client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=test_payload)
    used_server_options = server_patch.call_args[0][-1]
    assert {
        **config.SERVER_OPTIONS_DEFAULTS,
        **test_server_options,
    } == used_server_options


def test_start_notebook_with_no_server_options_specified(
    client,
    make_all_images_valid,
    make_server_args_valid,
    mock_server_start,
    kubernetes_client,
):
    payload = deepcopy(DEFAULT_PAYLOAD)
    # corresponds to server options not passed at all
    payload.pop("serverOptions")
    response = client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
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