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
import json
import re

import pytest

from renku_notebooks.api.classes.server import UserServer
from renku_notebooks.api.schemas.config_server_options import ServerOptionsDefaults
from renku_notebooks.config import config
from renku_notebooks.wsgi import app
from tests.integration.utils import find_session_js

SERVER_OPTIONS_NAMES_VALUES = [
    "cpu_request",
    "mem_request",
    "disk_request",
    "gpu_request",
]
SERVER_OPTIONS_NAMES_BOOL = [
    "lfs_auto_fetch",
]
SERVER_OPTIONS_NO_VALIDATION = [
    "defaultUrl",
]


@pytest.fixture(scope="session")
def server_options_defaults():
    return config.server_options.defaults


@pytest.fixture
def min_server_options(server_options_ui, server_options_defaults):
    output = {}
    for option_name, option in server_options_ui.items():
        if option["type"] == "enum":
            if option.get("allow_any_value", False):
                output[option_name] = option["value_range"]["min"]
            else:
                output[option_name] = option["options"][0]
        else:
            output[option_name] = option["default"]
    return ServerOptionsDefaults().load({**server_options_defaults, **output})


@pytest.fixture
def max_server_options(server_options_ui, server_options_defaults):
    output = {}
    for option_name, option in server_options_ui.items():
        if option["type"] == "enum":
            if option.get("allow_any_value", False):
                output[option_name] = option["value_range"]["max"]
            else:
                output[option_name] = option["options"][-1]
        else:
            output[option_name] = option["default"]
    return ServerOptionsDefaults().load({**server_options_defaults, **output})


@pytest.fixture
def valid_extra_range_options(server_options_ui):
    output = {}
    for option_name, option in server_options_ui.items():
        if option["type"] == "enum" and option.get("allow_any_value", False):
            output[option_name] = option["value_range"]["max"]
    return output


@pytest.fixture
def invalid_extra_range_options(server_options_ui, increase_value):
    output = {}
    for option_name in [
        *SERVER_OPTIONS_NAMES_VALUES,
        *SERVER_OPTIONS_NAMES_BOOL,
        *SERVER_OPTIONS_NO_VALIDATION,
    ]:
        if server_options_ui.get(option_name, {}).get(
            "type"
        ) == "enum" and server_options_ui.get(option_name, {}).get(
            "allow_any_value", False
        ):
            output[option_name] = increase_value(
                server_options_ui[option_name]["value_range"]["max"], 2
            )
        else:
            output[option_name] = "random-value"
    return output


@pytest.fixture
def increase_value():
    def _increase_value(value, increment):
        try:
            output = str(int(value) + increment)
        except ValueError:
            m = re.match(r"^([0-9\.]+)([^0-9\.]+)$", value)
            output = str(int(m.group(1)) + increment) + m.group(2)
        return output

    yield _increase_value


@pytest.fixture(
    params=[
        *SERVER_OPTIONS_NAMES_VALUES,
        *SERVER_OPTIONS_NAMES_BOOL,
        *SERVER_OPTIONS_NO_VALIDATION,
        "empty",
        "out_of_range",
    ]
)
def valid_server_options(request, min_server_options, valid_extra_range_options):
    if request.param == "empty":
        return {}
    elif request.param == "out_of_range":
        return valid_extra_range_options
    elif request.param in SERVER_OPTIONS_NO_VALIDATION:
        return {"defaultUrl": "/lab"}
    else:
        return {request.param: min_server_options[request.param]}


@pytest.fixture(
    params=[*SERVER_OPTIONS_NAMES_VALUES, *SERVER_OPTIONS_NAMES_BOOL, "out_of_range"]
)
def invalid_server_options(
    request, invalid_extra_range_options, max_server_options, increase_value
):
    if request.param == "out_of_range":
        return invalid_extra_range_options
    elif request.param in SERVER_OPTIONS_NAMES_BOOL:
        return {request.param: "wrong_type"}
    else:
        return {request.param: increase_value(max_server_options[request.param], 10)}


def test_can_start_notebook_with_valid_server_options(
    valid_server_options,
    start_session_and_wait_until_ready,
    valid_payload,
    gitlab_project,
    k8s_namespace,
    safe_username,
    server_options_defaults,
    headers,
):
    test_payload = {**valid_payload, "serverOptions": valid_server_options}
    response = start_session_and_wait_until_ready(headers, test_payload, gitlab_project)
    assert response is not None
    assert response.status_code == 201
    js = find_session_js(
        gitlab_project,
        k8s_namespace,
        safe_username,
        test_payload["commit_sha"],
        test_payload.get("branch", "master"),
    )
    assert js is not None
    with app.app_context():
        used_server_options = UserServer._get_server_options_from_js(js)
    assert {**server_options_defaults, **valid_server_options} == used_server_options


def test_can_not_start_notebook_with_invalid_options(
    invalid_server_options,
    launch_session,
    valid_payload,
    gitlab_project,
    k8s_namespace,
    safe_username,
    headers,
):
    payload = {**valid_payload, "serverOptions": invalid_server_options}
    response = launch_session(headers, payload, gitlab_project)
    assert response is not None and response.status_code == 422
    js = find_session_js(
        gitlab_project,
        k8s_namespace,
        safe_username,
        payload["commit_sha"],
        payload.get("branch", "master"),
    )
    assert js is None
