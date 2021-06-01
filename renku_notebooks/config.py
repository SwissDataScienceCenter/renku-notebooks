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
"""Notebooks service configuration."""
import os

from jupyterhub.services.auth import HubOAuth

from .util.misc import read_server_options_defaults, read_server_options_ui

GITLAB_URL = os.environ.get("GITLAB_URL", "https://gitlab.com")
"""The GitLab instance to use."""

IMAGE_REGISTRY = os.environ.get("IMAGE_REGISTRY", "")
"""The default image registry."""

JUPYTERHUB_ANNOTATION_PREFIX = "hub.jupyter.org/"
"""The prefix used for annotations by the KubeSpawner."""

JUPYTERHUB_API_TOKEN = os.environ.get("JUPYTERHUB_API_TOKEN", "")
"""The service api token."""

JUPYTERHUB_ADMIN_AUTH = HubOAuth(
    api_token=os.environ.get("JUPYTERHUB_API_TOKEN", "token"), cache_max_age=300
)
"""The oauth object used to query the JH API as an admin to get user information."""

JUPYTERHUB_URL = JUPYTERHUB_ADMIN_AUTH.api_url

JUPYTERHUB_ADMIN_HEADERS = {
    JUPYTERHUB_ADMIN_AUTH.auth_header_name: f"token {JUPYTERHUB_ADMIN_AUTH.api_token}"
}

JUPYTERHUB_ORIGIN = os.environ.get("JUPYTERHUB_ORIGIN", "")
"""Origin property of Jupyterhub, typically https://renkudomain.org"""

RENKU_ANNOTATION_PREFIX = "renku.io/"
"""The prefix used for annotations by Renku."""

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
"""Sentry client registration."""

SENTRY_ENV = os.environ.get("SENTRY_ENV", "")
"""Sentry client environment."""

SERVICE_PREFIX = os.environ.get("SERVICE_PREFIX", "/notebooks")
"""Service prefix is set by JupyterHub service spawner."""

JUPYTERHUB_AUTHENTICATOR = os.environ.get("JUPYTERHUB_AUTHENTICATOR", "gitlab")
"""How we are authenticating with jupyterhub"""

GITLAB_AUTH = JUPYTERHUB_AUTHENTICATOR == "gitlab"
"""Check if we're authenticating with GitLab (and thus have a GitLab oauth token)."""

JUPYTERHUB_PATH_PREFIX = os.environ.get("JUPYTERHUB_BASE_URL", "/jupyterhub")
"""Base path under which Jupyterhub is running."""

DEFAULT_IMAGE = os.environ.get("NOTEBOOKS_DEFAULT_IMAGE", "renku/singleuser:latest")
"""The default image to use for an interactive session if the image tied to the
current commit cannot be found."""

GIT_CLONE_IMAGE = os.environ.get("GIT_CLONE_IMAGE", "renku/git-clone:latest")
"""The image used to clone the git repository when a user session is started"""

GIT_HTTPS_PROXY_IMAGE = os.environ.get(
    "GIT_HTTPS_PROXY_IMAGE", "renku/git-https-proxy:latest"
)
"""The HTTPS proxy sidecar container image."""

NOTEBOOKS_SESSION_PVS_ENABLED = (
    os.environ.get("NOTEBOOKS_SESSION_PVS_ENABLED", "false") == "true"
)
"""Whether to use persistent volumes for user sessions.
Default is false, in which case ephemeral volumes are used."""

NOTEBOOKS_SESSION_PVS_STORAGE_CLASS = os.environ.get(
    "NOTEBOOKS_SESSION_PVS_STORAGE_CLASS",
)
"""Use a custom storage class for the user session persistent volumes."""

OPENAPI_VERSION = "2.0"
API_SPEC_URL = f"{SERVICE_PREFIX}/spec.json"

SERVER_OPTIONS_DEFAULTS = read_server_options_defaults()
SERVER_OPTIONS_UI = read_server_options_ui()

SESSIONS_HOST = "tasko.dev.renku.ch"
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "renku")
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET")
OIDC_TOKEN_URL = "https://tasko.dev.renku.ch/auth/realms/Renku/protocol/openid-connect/token"
OIDC_AUTH_URL = "https://tasko.dev.renku.ch/auth/realms/Renku/protocol/openid-connect/auth"

CRD_GROUP = "renku.io"
CRD_VERSION = "v1alpha1"
CRD_PLURAL = "jupyterservers"

SESSION_TLS_SECRET = "tasko-renku-ch-tls"
SESSION_INGRESS_ANNOTATIONS = '''{kubernetes.io/ingress.class: nginx,
nginx.ingress.kubernetes.io/proxy-body-size: "0",
nginx.ingress.kubernetes.io/proxy-buffer-size: 8k,
nginx.ingress.kubernetes.io/proxy-request-buffering: "off"}'''
