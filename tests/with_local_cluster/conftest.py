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
"""
Mocks and fixtures that are loaded automatically by pytest.
"""
import base64
import datetime
import json
import os
import re
import shutil

from unittest.mock import MagicMock

import escapism
import pytest
import responses

from tests.utils.classes import AttributeDictionary
from tests.utils.classes import K3DCluster

os.environ["NB_GIT__URL"] = "https://gitlab-url.com"
os.environ["NB_GIT__REGISTRY"] = "registry.gitlab-url.com"
os.environ["NB_SESSIONS__DEFAULT_IMAGE"] = "renku/singleuser:latest"
os.environ[
    "NB_SERVER_OPTIONS__DEFAULTS_PATH"
] = f"{os.getcwd()}/tests/unit/dummy_server_defaults.json"
os.environ[
    "NB_SERVER_OPTIONS__UI_CHOICES_PATH"
] = f"{os.getcwd()}/tests/unit/dummy_server_options.json"
os.environ["NB_SESSIONS__INGRESS__HOST"] = "renkulab.io"
os.environ["NB_SESSIONS__OIDC__CLIENT_SECRET"] = "oidc_client_secret"
os.environ["NB_SESSIONS__OIDC__TOKEN_URL"] = "http://localhost/token"
os.environ["NB_SESSIONS__OIDC__AUTH_URL"] = "http://localhost/auth"
os.environ["NB_K8S__ENABLED"] = "true"
os.environ["KUBECONFIG"] = ".k3d-config.yaml"


@pytest.fixture(scope="module", autouse=True)
def cluster():
    if shutil.which("k3d") is None:
        pytest.skip("Requires k3d for cluster creation")

    with K3DCluster("test-renku") as cluster:
        yield cluster


@pytest.fixture
def app():
    os.environ["NOTEBOOKS_SERVER_OPTIONS_DEFAULTS_PATH"] = "tests/unit/dummy_server_defaults.json"
    os.environ["NOTEBOOKS_SERVER_OPTIONS_UI_PATH"] = "tests/unit/dummy_server_options.json"
    from renku_notebooks.wsgi import app

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def git_params():
    url = "git_url"
    auth_header = "Bearer token"
    expires_at = datetime.datetime.now() + datetime.timedelta(hours=1)
    return {
        url: {"AuthorizationHeader": auth_header, "AccessTokenExpiresAt": expires_at.timestamp()}
    }


@pytest.fixture
def parsed_jwt():
    return {
        "sub": "userid",
        "email": "email",
        "iss": "oidc_issuer",
        "name": "John Doe",
        "preferred_username": "John Doe",
    }


@pytest.fixture
def proper_headers(parsed_jwt, git_params):
    return {
        "Renku-Auth-Id-Token": ".".join(
            [
                base64.b64encode(json.dumps({}).encode()).decode(),
                base64.b64encode(json.dumps(parsed_jwt).encode()).decode(),
                base64.b64encode(json.dumps({}).encode()).decode(),
            ]
        ),
        "Renku-Auth-Git-Credentials": base64.b64encode(json.dumps(git_params).encode()).decode(),
        "Renku-Auth-Access-Token": "test",
        "Renku-Auth-Refresh-Token": "test refresh",
    }


@pytest.fixture
def user_with_project_path():
    def _user_with_project_path(path):
        user = MagicMock()
        renku_project = MagicMock()
        renku_project.path_with_namespace = path
        user.get_renku_project.return_value = renku_project
        user.username = "John Doe"
        user.safe_username = escapism.escape(user.username, escape_char="-").lower()
        return user

    yield _user_with_project_path


@pytest.fixture
def mock_data_svc(monkeypatch):
    """Mock data services."""

    data_svc_url = "http://renku-data-service"
    _test_resource_pools = [
        {
            "name": "test-name",
            "classes": [
                {
                    "cpu": 0.1,
                    "memory": 10,
                    "gpu": 0,
                    "name": "test-class-name",
                    "max_storage": 100,
                    "default_storage": 1,
                    "default": True,
                    "node_affinities": [],
                    "tolerations": [],
                }
            ],
            "quota": {"cpu": 100, "memory": 100, "gpu": 0},
            "default": True,
            "public": True,
        }
    ]

    monkeypatch.setenv("RENKU_ACCESS_TOKEN", "abcdefg")
    monkeypatch.setenv("DATA_SERVICE_URL", data_svc_url)
    with responses.RequestsMock() as rsps:
        rsps.add_passthru(re.compile("https://.+\\.docker\\..+"))
        rsps.add_passthru(re.compile("http\\+docker://localhost/\\.*"))

        rsps.get(f"{data_svc_url}/resource_pools", json=_test_resource_pools, status=200)

        watcher_matcher = re.compile("http://renku-k8s-watcher/servers/.*")
        rsps.get(watcher_matcher, json={}, status=200)

        from renku_notebooks.config import config

        rsps.post(
            config.user_secrets.secrets_storage_service_url + "/api/secrets/k8s_secret", status=201
        )

        yield


@pytest.fixture
def fake_gitlab_projects():
    class GitLabProject(AttributeDictionary):
        def __init__(self):
            super().__init__({})

        def get(self, name, default=None):
            if name not in self:
                return AttributeDictionary(
                    {
                        "path": "my-test",
                        "path_with_namespace": "test-namespace/my-test",
                        "branches": {"main": AttributeDictionary({})},
                        "commits": {
                            "ee4b1c9fedc99abe5892ee95320bbd8471c5985b": AttributeDictionary({})
                        },
                        "id": 5407,
                        "http_url_to_repo": "https://gitlab-url.com/test-namespace/my-test.git",
                        "web_url": "https://gitlab-url.com/test-namespace/my-test",
                    }
                )
            return super().get(name, default)

    return GitLabProject()


@pytest.fixture()
def fake_gitlab(mocker, fake_gitlab_projects):

    gitlab = mocker.patch("renku_notebooks.api.classes.user.Gitlab")
    gitlab_mock = MagicMock()
    gitlab_mock.auth = MagicMock()
    gitlab_mock.projects = fake_gitlab_projects
    gitlab_mock.user = AttributeDictionary(
        {"username": "john.doe", "name": "John Doe", "email": "john.doe@notebooks-tests.renku.ch"}
    )
    gitlab_mock.url = "https://gitlab-url.com"
    gitlab.return_value = gitlab_mock
    return gitlab
