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
"""Notebooks service API."""
from flask import abort, current_app, request, make_response, jsonify, Blueprint
from flask_apispec import use_kwargs
import escapism
import json
from marshmallow import Schema, fields
import os
from urllib.parse import urlparse
from uuid import uuid4

from ... import config
from ...util.check_image import get_docker_token, image_exists, parse_image_name
from ...util.gitlab_ import get_renku_project
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
from .utils import _read_server_options_file


bp = Blueprint("servers_post_blueprint", __name__, url_prefix=config.SERVICE_PREFIX,)


class RequestSchema(Schema):
    namespace = fields.Str(required=True)
    project = fields.Str(required=True)
    branch = fields.Str(missing="master")
    commit_sha = fields.Str(required=True)
    notebook = fields.Str(missing=None)
    image = fields.Str(missing=None)


@bp.route("servers", methods=["POST"])
@use_kwargs(RequestSchema(), location="json", apply=True)
@authenticated
def launch_notebook(user, namespace, project, branch, commit_sha, notebook, image):
    """Launch user server with a given arguments."""
    requested_image = image

    # 0. check if server already exists and if so return it
    server_name = make_server_name(namespace, project, branch, commit_sha)

    current_app.logger.debug(
        f"Request to create server: {server_name} for user: {user}"
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

    gl_project = get_renku_project(user, f"{namespace}/{project}")

    if gl_project is None:
        return current_app.response_class(
            status=404,
            response=f"Cannot find project {project} for user: {user['name']}.",
        )

    # set the notebook image if not specified in the request
    if requested_image is None:
        parsed_image = {
            "hostname": config.IMAGE_REGISTRY,
            "image": gl_project.path_with_namespace.lower(),
            "tag": commit_sha[:7],
        }
        commit_image = (
            f"{config.IMAGE_REGISTRY}/{gl_project.path_with_namespace.lower()}"
            f":{commit_sha[:7]}"
        )
    else:
        parsed_image = parse_image_name(requested_image)
    # get token
    token, is_image_private = get_docker_token(**parsed_image, user=user)
    # check if images exist
    image_exists_result = image_exists(**parsed_image, token=token)
    # assign image
    if image_exists_result and requested_image is None:
        # the image tied to the commit exists
        image = commit_image
    elif not image_exists_result and requested_image is None:
        # the image tied to the commit does not exist, fallback to default image
        image = config.DEFAULT_IMAGE
        is_image_private = False
        current_app.logger.debug(
            f"Image for the selected commit {commit_sha} of {project}"
            f" not found, using default image {config.DEFAULT_IMAGE}"
        )
    elif image_exists_result and requested_image is not None:
        # a specific image was requested and it exists
        image = requested_image
    else:
        # a specific image was requested but does not exist
        return make_response(
            jsonify({"error": f"Cannot find/access image {requested_image}."}), 404
        )

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
    if config.GITLAB_AUTH and is_image_private:
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
