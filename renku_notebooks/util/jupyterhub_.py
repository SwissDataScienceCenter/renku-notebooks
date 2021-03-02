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
"""Functions for interfacing with JupyterHub."""

from hashlib import md5
import requests

from ..api.classes import User


def make_server_name(namespace, project, branch, commit_sha):
    """Form a 16-digit hash server ID."""
    server_string = f"{namespace}{project}{branch}{commit_sha}"
    return "{project}-{hash}".format(
        project=project[:54], hash=md5(server_string.encode()).hexdigest()[:8]
    )


def create_named_server(user, server_name, payload):
    """Create a named-server for user"""
    user = User()
    return requests.post(
        f"{user.prefix}/users/{user.user['name']}/servers/{server_name}",
        json=payload,
        headers=user.headers,
    )


def delete_named_server(user, server_name):
    """Delete a named-server"""
    user = User()
    return requests.delete(
        f"{user.prefix}/users/{user.user['name']}/servers/{server_name}",
        headers=user.headers,
    )
