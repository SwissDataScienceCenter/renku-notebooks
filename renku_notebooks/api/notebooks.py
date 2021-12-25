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
from time import sleep

from flask import Blueprint, current_app, request, make_response
from flask_apispec import use_kwargs, doc, marshal_with
from marshmallow import fields

from .. import config
from .auth import authenticated
from .schemas import (
    LaunchNotebookRequest,
    LaunchNotebookResponse,
    ServersGetRequest,
    ServersGetResponse,
    ServerLogs,
    ServerOptionsUI,
    AutosavesList,
)
from .classes.server import UserServer
from .classes.storage import Autosave
from ..errors import (
    MissingResourceError,
    UserInputError,
    IntermittentError,
    GenericError,
)


bp = Blueprint("notebooks_blueprint", __name__, url_prefix=config.SERVICE_PREFIX)


@bp.route("servers", methods=["GET"])
@use_kwargs(ServersGetRequest(), location="query")
@marshal_with(ServersGetResponse(), code=200, description="List of all servers")
@doc(tags=["servers"], summary="Information about all active servers.")
@authenticated
def user_servers(user, **query_params):
    """Return a JSON of running servers for the user."""
    servers = [UserServer.from_js(user, js) for js in user.jss]
    filter_attrs = list(filter(lambda x: x[1] is not None, query_params.items()))
    filtered_servers = {}
    for server in servers:
        if all([getattr(server, key, value) == value for key, value in filter_attrs]):
            filtered_servers[server.server_name] = server
    return {"servers": filtered_servers}


@bp.route("servers/<server_name>", methods=["GET"])
@marshal_with(LaunchNotebookResponse(), code=200, description="Server properties.")
@doc(tags=["servers"], summary="Information about an active server.")
@authenticated
def user_server(user, server_name):
    """Returns a user server based on its ID"""
    server = UserServer.from_server_name(user, server_name)
    if server is not None:
        return server
    raise MissingResourceError(
        message=f"The requested server {server_name} cannot be found.",
        detail=(
            "This can happen if you have mistyped the server name, "
            "logged in with different credentials or have deleted "
            "the server you are requesting."
        ),
    )


@bp.route("servers", methods=["POST"])
@marshal_with(
    LaunchNotebookResponse(),
    code=200,
    description="The server exists and is already running.",
)
@marshal_with(
    LaunchNotebookResponse(),
    code=201,
    description="The requested server has been created.",
)
@use_kwargs(LaunchNotebookRequest(), location="json")
@doc(tags=["servers"], summary="Start a server.")
@authenticated
def launch_notebook(
    user, namespace, project, branch, commit_sha, notebook, image, server_options
):
    server = UserServer(
        user, namespace, project, branch, commit_sha, notebook, image, server_options
    )

    if len(server.safe_username) > 63:
        raise UserInputError(
            message="A username cannot be longer than 63 characters, "
            f"your username is {len(server.safe_username)} characters long.",
            detail="This can occur if your username has been changed manually or by an admin.",
        )

    server.get_js()
    if server.server_exists():
        return server, 200

    try:
        server.start()
    except GenericError:
        current_app.logger.warning(
            f"Creating server {server.server_name} failed, retrying once."
        )
        sleep(1)
        server.start()

    current_app.logger.debug(f"Server {server.server_name} has been started")
    for autosave in user.get_autosaves(server.gl_project.path_with_namespace):
        autosave.cleanup(server.commit_sha)
    return server, 201


@bp.route("servers/<server_name>", methods=["DELETE"])
@doc(
    tags=["servers"],
    summary="Stop a running server.",
    responses={
        204: {"description": "The server was stopped."},
    },
)
@use_kwargs({"forced": fields.Bool(missing=False, data_key="force")}, location="query")
@authenticated
def stop_server(user, forced, server_name):
    """Stop user server with name."""
    current_app.logger.debug(
        f"Request to delete server: {server_name} forced: {forced}."
    )
    server = UserServer.from_server_name(user, server_name)
    if server is None:
        raise MissingResourceError(
            message=f"The server {server_name} you are trying to stop does not exist."
        )
    else:
        status = server.stop(forced)
        if status is not None:
            return "", 204
        else:
            raise IntermittentError(message=f"Cannot delete the server {server_name}")


@bp.route("server_options", methods=["GET"])
@marshal_with(
    ServerOptionsUI(),
    code=200,
    description="The options shown in the UI when starting a server.",
)
@doc(tags=["servers"], summary="Get server options")
@authenticated
def server_options(user):
    """Return a set of configurable server options."""
    # TODO: append image-specific options to the options json
    return current_app.config["SERVER_OPTIONS_UI"]


@bp.route("logs/<server_name>", methods=["GET"])
@doc(
    tags=["logs"],
    summary="Get server logs",
    # marshmallow does not allow arrays at top level
    # this is a way to bypass that in the docs
    responses={
        200: {
            "examples": {
                "application/json": ["Line 1 of logs", "Line 2 of logs"],
                "text/plain": ["Line 1 of logs", "Line 2 of logs"],
            }
        }
    },
)
@marshal_with(ServerLogs(), code=200, description="List of server logs.")
@authenticated
def server_logs(user, server_name):
    """Return the logs of the running server."""
    server = UserServer.from_server_name(user, server_name)
    if server is not None:
        max_lines = request.args.get("max_lines", default=250, type=int)
        logs = server.get_logs(max_lines)
        if logs is not None:
            return {"items": str.splitlines(logs)}, 200
    raise MissingResourceError(
        message=f"The server {server_name} you are trying to get logs for does not exist."
    )


@bp.route("<path:namespace_project>/autosave", methods=["GET"])
@doc(
    tags=["autosave"],
    summary="Information about autosaved and recovered work from user sessions.",
    responses={
        200: {"description": "All the autosave branches or PVs for the project."},
    },
)
@marshal_with(AutosavesList(), code=200, description="List of autosaves.")
@authenticated
def autosave_info(user, namespace_project):
    """Information about all autosaves for a project."""
    if user.get_renku_project(namespace_project) is None:
        raise MissingResourceError(message=f"Cannot find project {namespace_project}")
    return {
        "pvsSupport": current_app.config["NOTEBOOKS_SESSION_PVS_ENABLED"],
        "autosaves": user.get_autosaves(namespace_project),
    }


@bp.route(
    "<path:namespace_project>/autosave/<path:autosave_name>",
    methods=["DELETE"],
)
@doc(
    tags=["autosave"],
    summary="Delete an autosave PV and or branch.",
    responses={
        204: {"description": "The autosave branch and/or PV has been deleted."},
    },
)
@authenticated
def delete_autosave(user, namespace_project, autosave_name):
    """Delete an autosave PV and or branch."""
    if user.get_renku_project(namespace_project) is None:
        raise MissingResourceError(message=f"Cannot find project {namespace_project}")
    autosave = Autosave.from_name(user, namespace_project, autosave_name)
    if not autosave.exists:
        raise MissingResourceError(
            message=f"The autosave branch {autosave_name} does not exist"
        )
    autosave.delete()
    return make_response("", 204)
