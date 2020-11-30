# -*- coding: utf-8 -*-
#
# Copyright 2020 - Swiss Data Science Center (SDSC)
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
"""Plugin script for mitmproxy to add headers for https repository access."""
from base64 import b64encode
import os
import sys

# TODO: This configuration could be turned into an entire list
# TODO: of token/url pairs provided as a secret by the notebook service.
gitlab_oauth_token = os.environ.get("GITLAB_OAUTH_TOKEN")
repository_url = os.environ.get("REPOSITORY_URL")

basic_auth_header = (
    f"Basic {b64encode(f'oauth2:{gitlab_oauth_token}'.encode()).decode()}"
)


def request(flow):
    if not gitlab_oauth_token:
        sys.stdout.write("GitLab oauth token is missing - aborting...")
        return
    if not repository_url:
        sys.stdout.write("Repository url is missing - aborting...")
        return
    if flow.request.url.startswith(repository_url):
        flow.request.headers["Authorization"] = basic_auth_header
