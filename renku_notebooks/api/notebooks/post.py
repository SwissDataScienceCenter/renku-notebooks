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
"""Notebooks service API."""
import json
import os
from urllib.parse import urlparse
from uuid import uuid4

import escapism
from flask import abort, current_app, request

from ... import config
from ...util.gitlab_ import (
    get_notebook_image,
    get_project,
)
from ...util.jupyterhub_ import (
    make_server_name,
    create_named_server,
    check_user_has_named_server,
)
from ...util.kubernetes_ import (
    get_user_server,
    create_registry_secret,
)
from ..auth import authenticated
from .blueprints import servers_bp
from .utils import _read_server_options_file


@servers_bp.route("servers", methods=["POST"])
@authenticated
def launch_notebook(user):
    """Launch user server with a given arguments."""
    try:
        payload = request.json
        namespace = payload["namespace"]
        project = payload["project"]
        branch = payload.get("branch", "master")
        commit_sha = payload["commit_sha"]
        notebook = payload.get("notebook")
    except (AttributeError, KeyError):
        return current_app.response_class(
            status=400,
            response="Invalid payload. 'namespace', 'project', and 'commit_sha' are mandatory.",
        )

    # 0. check if server already exists and if so return it
    server_name = make_server_name(namespace, project, branch, commit_sha)

    current_app.logger.debug(
        f"Request to create server: {server_name} with options: {payload} for user: {user}"
    )

    if check_user_has_named_server(user, server_name):
        server = get_user_server(user, server_name)
        current_app.logger.debug(
            f"Server {server_name} already exists in JupyterHub: {server}"
        )
        return current_app.response_class(
            response=json.dumps(server), status=200, mimetype="application/json"
        )

    # 1. launch using spawner that checks the access

    # process the server options
    # server options from system configuration
    server_options_defaults = _read_server_options_file()

    # process the requested options and set others to defaults from config
    server_options = (request.get_json() or {}).get("serverOptions", {})
    server_options.setdefault(
        "defaultUrl",
        server_options_defaults.pop("defaultUrl", {}).get(
            "default", os.getenv("JUPYTERHUB_SINGLEUSER_DEFAULT_URL")
        ),
    )

    for key in server_options_defaults.keys():
        server_options.setdefault(key, server_options_defaults.get(key)["default"])

    gl_project = get_project(user, namespace, project)

    if gl_project is None:
        return current_app.response_class(
            status=404,
            response=f"Cannot find project {project} for user: {user['name']}.",
        )

    # set the notebook image
    image = get_notebook_image(user, namespace, project, commit_sha)

    payload = {
        "namespace": namespace,
        "project": project,
        "branch": branch,
        "commit_sha": commit_sha,
        "project_id": gl_project.id,
        "notebook": notebook,
        "image": image,
        "git_clone_image": os.getenv("GIT_CLONE_IMAGE", "renku/git-clone:latest"),
        "server_options": server_options,
    }

    current_app.logger.debug(f"Creating server {server_name} with {payload}")

    # only create a pull secret if the project has limited visibility and a token is available
    if config.GITLAB_AUTH and gl_project.visibility in {"private", "internal"}:
        git_host = urlparse(config.GITLAB_URL).netloc
        safe_username = escapism.escape(user.get("name"), escape_char="-").lower()
        secret_name = f"{safe_username}-registry-{str(uuid4())}"
        create_registry_secret(
            user, namespace, secret_name, project, commit_sha, git_host
        )
        payload["image_pull_secrets"] = [secret_name]

    r = create_named_server(user, server_name, payload)

    # 2. check response, we expect:
    #   - HTTP 201 if the server is already running; in this case redirect to it
    #   - HTTP 202 if the server is spawning
    if r.status_code == 201:
        current_app.logger.debug(f"server {server_name} already running")
    elif r.status_code == 202:
        current_app.logger.debug(f"spawn initialized for {server_name}")
    elif r.status_code == 400:
        current_app.logger.debug("server in pending state")
    else:
        current_app.logger.error(
            f"creating server {server_name} failed with {r.status_code}"
        )
        # unexpected status code, abort
        abort(r.status_code)

    # fetch the server
    server = get_user_server(user, server_name)
    return current_app.response_class(
        response=json.dumps(server), status=r.status_code, mimetype="application/json"
    )
