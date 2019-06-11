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
"""Dummy JupyterHub configuration used for testing."""
import os
import simplespawner

from jupyterhub_traefik_proxy import TraefikTomlProxy


class DummySpawner(simplespawner.SimpleLocalProcessSpawner):
    def get_state(self):
        state = super().get_state()
        state["pod_name"] = "dummy-pod-name"
        return state


c = get_config()  # noqa

c.JupyterHub.allow_named_servers = True

c.JupyterHub.spawner_class = DummySpawner

c.JupyterHub.proxy_class = TraefikTomlProxy
c.TraefikTomlProxy.should_start = False
c.TraefikTomlProxy.traefik_api_username = "api_admin"
c.TraefikTomlProxy.traefik_api_password = "admin"
c.TraefikTomlProxy.toml_dynamic_config_file = os.path.join(
    os.path.dirname(__file__), "rules.toml"
)

c.JupyterHub.api_tokens = {"8f7e09b3bf6b8a20": "dummyuser"}

c.JupyterHub.services = [
    {
        "name": "renku-test-notebook-services",
        "api_token": "03b0421755116015fe8b44d53d7fc0cc",
        "admin": True,
    }
]
