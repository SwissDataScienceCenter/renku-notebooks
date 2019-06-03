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
"""Tests for accessibility of test JupyterHub instance."""
import requests


def test_can_get_user_info_from_jupyterhub():
    response = requests.get(
        "http://localhost:19000/hub/api/users/dummyuser",
        headers={"Authorization": "token 8f7e09b3bf6b8a20"},
    )
    assert response.status_code == 200
    assert response.json().get("name") == "dummyuser"
