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
import json
from time import sleep

from flask import Blueprint, current_app, jsonify, request, make_response
from flask_apispec import use_kwargs, doc
from marshmallow import fields

from .. import config
from ..util.kubernetes_ import (
    get_all_user_pods,
    filter_pods_by_annotations,
    get_k8s_client,
    format_user_pod_data,
)
from .auth import authenticated
from .decorators import validate_response_with
from .schemas import (
    LaunchNotebookRequest,
    LaunchNotebookResponse,
    ServersGetResponse,
    ServerLogs,
    ServerOptions,
    FailedParsing,
)
from ..util.misc import read_server_options_file
from .classes.server import Server


bp = Blueprint("notebooks_blueprint", __name__, url_prefix=config.SERVICE_PREFIX)


@bp.route("servers")
@validate_response_with(
    {200: {"schema": ServersGetResponse(), "description": "List of all servers."}}
)
@doc(tags=["servers"], summary="Information about all active servers.")
@authenticated
def user_servers(user):
    """Return a JSON of running servers for the user."""
    k8s_client, k8s_namespace = get_k8s_client()
    user_pods = get_all_user_pods(user, k8s_client, k8s_namespace)
    annotations = {}
    for annotation_name in request.args.keys():
        if request.args[annotation_name] is not None:
            annotations[
                config.RENKU_ANNOTATION_PREFIX + annotation_name
            ] = request.args[annotation_name]
    if len(annotations.items()) > 0:
        selected_pods = filter_pods_by_annotations(user_pods, annotations)
    else:
        selected_pods = user_pods
    formatted_response = {}
    for pod in selected_pods:
        data = format_user_pod_data(
            pod,
            config.JUPYTERHUB_PATH_PREFIX,
            config.DEFAULT_IMAGE,
            config.RENKU_ANNOTATION_PREFIX,
            config.JUPYTERHUB_ORIGIN,
        )
        formatted_response[data["annotations"]["hub.jupyter.org/servername"]] = data
    return jsonify({"servers": formatted_response})


@bp.route("servers/<server_name>")
@validate_response_with(
    {200: {"schema": LaunchNotebookResponse(), "description": "Server properties."}}
)
@doc(tags=["servers"], summary="Information about an active server.")
@authenticated
def user_server(user, server_name):
    """Returns a user server based on its ID"""
    server = Server.from_server_name(user, server_name)
    if server is not None:
        summary = server.k8s_summary()
        if summary is not None:
            return jsonify(summary)
    return make_response(jsonify({"messages": {"error": "Cannot find server"}}), 404)


@bp.route("servers", methods=["POST"])
@validate_response_with(
    {
        200: {
            "schema": LaunchNotebookResponse(),
            "description": "The request to create the server has been submitted.",
        },
        201: {
            "schema": LaunchNotebookResponse(),
            "description": "The requested server is already running.",
        },
        202: {
            "schema": LaunchNotebookResponse(),
            "description": "The requested server is still spawning.",
        },
        400: {
            "schema": LaunchNotebookResponse(),
            "description": "The requested server is in pending state.",
        },
        422: {"schema": FailedParsing(), "description": "Invalid request."},
    }
)
@use_kwargs(LaunchNotebookRequest(), location="json")
@doc(tags=["servers"], summary="Start a server.")
@authenticated
def launch_notebook(
    user, namespace, project, branch, commit_sha, notebook, image, server_options
):
    server = Server(
        user, namespace, project, branch, commit_sha, notebook, image, server_options
    )

    if server.server_exists():
        return current_app.response_class(
            response=json.dumps(server.k8s_summary()),
            status=200,
            mimetype="application/json",
        )

    r = server.start()
    if r.status_code == 500:
        current_app.logger.warning(
            f"Creating server {server.server_name} failed with status code 500, retrying once."
        )
        sleep(1)
        r = server.start()
    # check response, we expect:
    #   - HTTP 201 if the server is already running
    #   - HTTP 202 if the server is spawning
    status_code = r.status_code
    if status_code == 201:
        current_app.logger.debug(f"server {server.server_name} already running")
        return current_app.response_class(
            response=json.dumps(server.k8s_summary()),
            status=201,
            mimetype="application/json",
        )
    elif status_code == 202:
        current_app.logger.debug(f"spawn initialized for {server.server_name}")
        return current_app.response_class(
            response=json.dumps(server.k8s_summary()),
            status=202,
            mimetype="application/json",
        )
    elif status_code == 400:
        current_app.logger.debug("server in pending state")
        return current_app.response_class(
            response=json.dumps(server.k8s_summary()),
            status=400,
            mimetype="application/json",
        )
    elif status_code == 404:
        current_app.logger.debug(
            "Branch, commit, namespace, image or project does not exist"
        )
        return r
    else:
        current_app.logger.error(
            f"creating server {server.server_name} failed with {status_code}"
        )
        # unexpected status code, abort
        return make_response(
            jsonify(
                {
                    "messages": {
                        "error": f"creating server {server.server_name} failed with "
                        f"{status_code} from jupyterhub",
                    }
                }
            ),
            500,
        )


@bp.route("servers/<server_name>", methods=["DELETE"])
@doc(
    tags=["servers"],
    summary="Stop a running server.",
    responses={
        204: {"description": "The server was stopped."},
        202: {
            "description": "The server was not stopped, it is taking a while to stop."
        },
        400: {
            "description": "Only for 'force-delete', cannot force delete the server."
        },
        404: {"description": "The server cannot be found."},
    },
)
@validate_response_with(
    {422: {"schema": FailedParsing(), "description": "Invalid request."}}
)
@use_kwargs({"forced": fields.Bool(missing=False, data_key="force")}, location="query")
@authenticated
def stop_server(user, forced, server_name):
    """Stop user server with name."""
    current_app.logger.debug(
        f"Request to delete server: {server_name} forced: {forced} for user: {user}"
    )
    server = Server.from_server_name(user, server_name)
    if server is None:
        return make_response(
            jsonify({"messages": {"error": "Cannot find server"}}), 404
        )
    return server.delete(forced)


@bp.route("server_options")
@validate_response_with(
    {
        200: {
            "schema": ServerOptions(),
            "description": "The options available when starting a server.",
        }
    }
)
@doc(tags=["servers"], summary="Get server options")
@authenticated
def server_options(user):
    """Return a set of configurable server options."""
    server_options = read_server_options_file()

    # TODO: append image-specific options to the options json
    return jsonify(server_options)


@bp.route("logs/<server_name>")
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
            },
        }
    },
)
@validate_response_with(
    {200: {"schema": ServerLogs(), "description": "List of server logs."}}
)
@authenticated
def server_logs(user, server_name):
    """Return the logs of the running server."""
    server = Server.from_server_name(user, server_name)
    if server is not None:
        max_lines = request.args.get("max_lines", default=250, type=int)
        logs = server.logs(max_lines)
        if logs is not None:
            return jsonify({"items": str.splitlines(logs)})
    return make_response(jsonify({"messages": {"error": "Cannot find server"}}), 404)
