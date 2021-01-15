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
"""Tests for authentication functions."""
import pytest


AUTHORIZED_HEADERS = {"Authorization": "token 8f7e09b3bf6b8a20"}
UNAUTHORIZED_HEADERS = {"Authorization": "token 8f7e09b3"}
HEADERS_WITHOUT_AUTHORIZATION = {}


def test_can_get_user_info(client, kubernetes_client_empty):
    response = client.get("/service/user", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 200
    assert response.json.get("name") == "dummyuser"


@pytest.mark.parametrize(
    "headers", [UNAUTHORIZED_HEADERS.copy(), HEADERS_WITHOUT_AUTHORIZATION.copy()]
)
def test_unauthorized_access_with_json_mime_type_returns_401(headers, client):
    headers.update({"Accept": "application/json"})
    response = client.get("/service/user", headers=headers)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "headers", [UNAUTHORIZED_HEADERS.copy(), HEADERS_WITHOUT_AUTHORIZATION.copy()]
)
def test_unauthorized_access_with_non_json_mime_type_returns_302(headers, client):
    headers = UNAUTHORIZED_HEADERS.copy()
    headers.update({"Accept": "text/html"})
    response = client.get("/service/user", headers=headers)
    assert response.status_code == 302


@pytest.mark.skip(reason="How to test /service/oauth_callback endpoint?")
def test_oauth_callback():
    pass
