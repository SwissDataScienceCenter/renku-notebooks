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
from flask import Blueprint, current_app, jsonify, make_response
from marshmallow import fields, validate
from webargs.flaskparser import use_args

from ..config import config
from ..errors.user import ImageParseError, MissingResourceError, UserInputError
from ..util.check_image import get_docker_token, image_exists, parse_image_name
from ..util.kubernetes_ import make_server_name
from .auth import authenticated
from .classes.crac import CRACValidator, DummyCRACValidator
from .classes.server import UserServer
from .classes.server_manifest import UserServerManifest
from .classes.storage import AutosaveBranch
from .schemas.autosave import AutosavesList
from .schemas.config_server_options import ServerOptionsEndpointResponse
from .schemas.logs import ServerLogs
from .schemas.server_options import ServerOptions
from .schemas.servers_get import NotebookResponse, ServersGetRequest, ServersGetResponse
from .schemas.servers_post import LaunchNotebookRequest
from .schemas.version import VersionResponse

bp = Blueprint("notebooks_blueprint", __name__, url_prefix=config.service_prefix)


@bp.route("/version")
def version():
    """
    Return notebook services version.

    ---
    get:
      description: Information about notebooks service.
      responses:
        200:
          description: Notebooks service info.
          content:
            application/json:
              schema: VersionResponse
    """
    info = {
        "name": "renku-notebooks",
        "versions": [
            {
                "version": config.version,
                "data": {
                    "anonymousSessionsEnabled": config.anonymous_sessions_enabled,
                    "cloudstorageEnabled": {
                        "s3": config.cloud_storage.s3.enabled,
                        "azure_blob": config.cloud_storage.azure_blob.enabled,
                    },
                    "sshEnabled": config.ssh_enabled,
                },
            }
        ],
    }
    return VersionResponse().dump(info), 200


@bp.route("servers", methods=["GET"])
@use_args(ServersGetRequest(), location="query", as_kwargs=True)
@authenticated
def user_servers(user, **query_params):
    """
    Return a JSON of running servers for the user.

    ---
    get:
      description: Information about all active servers for a user.
      parameters:
        - in: query
          schema: ServersGetRequest
      responses:
        200:
          description: Map of all servers for a user.
          content:
            application/json:
              schema: ServersGetResponse
      tags:
        - servers
    """
    servers = [
        UserServerManifest(s)
        for s in config.k8s.client.list_servers(user.safe_username)
    ]
    filter_attrs = list(filter(lambda x: x[1] is not None, query_params.items()))
    filtered_servers = {}
    ann_prefix = config.session_get_endpoint_annotations.renku_annotation_prefix
    for server in servers:
        if all(
            [
                server.annotations.get(f"{ann_prefix}{key}") == value
                for key, value in filter_attrs
            ]
        ):
            filtered_servers[server.server_name] = server
    return ServersGetResponse().dump({"servers": filtered_servers})


@bp.route("servers/<server_name>", methods=["GET"])
@use_args(
    {"server_name": fields.Str(required=True)}, location="view_args", as_kwargs=True
)
@authenticated
def user_server(user, server_name):
    """
    Returns a user server based on its ID.

    ---
    get:
      description: Information about an active server.
      parameters:
        - in: path
          schema:
            type: string
          required: true
          name: server_name
          description: The name of the server for which additional information is required.
      responses:
        200:
          description: Server properties.
          content:
            application/json:
              schema: NotebookResponse
        404:
          description: The specified server does not exist.
          content:
            application/json:
              schema: ErrorResponse
      tags:
        - servers
    """
    server = config.k8s.client.get_server(server_name, user.safe_username)
    if server is None:
        raise MissingResourceError(message=f"The server {server_name} does not exist.")
    server = UserServerManifest(server)
    return jsonify(NotebookResponse().dump(server))


@bp.route("servers", methods=["POST"])
@use_args(LaunchNotebookRequest(), location="json", as_kwargs=True)
@authenticated
def launch_notebook(
    user,
    namespace,
    project,
    branch,
    commit_sha,
    notebook,
    image,
    resource_class_id,
    storage,
    environment_variables,
    default_url,
    lfs_auto_fetch,
    cloudstorage=None,
    server_options=None,
):
    """
    Launch a Jupyter server.

    ---
    post:
      description: Start a server.
      requestBody:
        content:
          application/json:
            schema: LaunchNotebookRequest
      responses:
        200:
          description: The server exists and is already running.
          content:
            application/json:
              schema: NotebookResponse
        201:
          description: The requested server has been created.
          content:
            application/json:
              schema: NotebookResponse
        404:
          description: The server could not be launched.
          content:
            application/json:
              schema: ErrorResponse
      tags:
        - servers
    """
    crac_validator = CRACValidator(config.crac_url)
    if config.dummy_stores:
        crac_validator = DummyCRACValidator()
    server_name = make_server_name(
        user.safe_username, namespace, project, branch, commit_sha
    )
    server = config.k8s.client.get_server(server_name, user.safe_username)
    if server:
        return NotebookResponse().dump(UserServerManifest(server)), 200

    parsed_server_options = None
    if resource_class_id is not None:
        # A resource class ID was passed in, validate with CRAC servuce
        parsed_server_options = crac_validator.validate_class_storage(
            user, resource_class_id, storage
        )
    elif server_options is not None:
        # The old style API was used, try to find a matching class from the CRAC service
        requested_server_options = ServerOptions(
            memory=server_options["mem_request"],
            storage=server_options["disk_request"],
            cpu=server_options["cpu_request"],
            gpu=server_options["gpu_request"],
            lfs_auto_fetch=server_options["lfs_auto_fetch"],
            default_url=server_options["defaultUrl"],
        )
        parsed_server_options = crac_validator.find_acceptable_class(
            user, requested_server_options
        )
        if parsed_server_options is None:
            raise UserInputError(
                message="Cannot find suitable server options based on your request and "
                "the available resource classes.",
                detail="You are receiving this error because you are using the old API for "
                "selecting resources. Updating to the new API which includes specifying only "
                "a specific resource class ID and storage is preferred and more convenient.",
            )
    else:
        # No resource class ID specified or old-style server options, use defaults from CRAC
        default_resource_class = crac_validator.get_default_class()
        max_storage_gb = default_resource_class.get("max_storage", 0)
        if storage is not None and storage > max_storage_gb:
            raise UserInputError(
                "The requested storage amount is higher than the "
                f"allowable maximum for the default resource class of {max_storage_gb}GB."
            )
        if storage is None:
            storage = default_resource_class.get("default_storage")
        parsed_server_options = ServerOptions.from_resource_class(
            default_resource_class
        )
        # ServerOptions stores memory and storage in bytes, but storage in request is in GB
        parsed_server_options.storage = storage * 1000000000

    if default_url is not None:
        parsed_server_options.default_url = default_url

    if lfs_auto_fetch is not None:
        parsed_server_options.lfs_auto_fetch = lfs_auto_fetch

    server = UserServer(
        user,
        namespace,
        project,
        branch,
        commit_sha,
        notebook,
        image,
        parsed_server_options,
        environment_variables,
        cloudstorage or [],
        config.k8s.client,
    )

    if len(server.safe_username) > 63:
        raise UserInputError(
            message="A username cannot be longer than 63 characters, "
            f"your username is {len(server.safe_username)} characters long.",
            detail="This can occur if your username has been changed manually or by an admin.",
        )

    manifest = server.start()

    current_app.logger.debug(f"Server {server.server_name} has been started")
    for autosave in user.get_autosaves(server.gl_project.path_with_namespace):
        autosave.cleanup(server.commit_sha)
    return NotebookResponse().dump(UserServerManifest(manifest)), 201


@bp.route("servers/<server_name>", methods=["DELETE"])
@use_args(
    {"server_name": fields.Str(required=True)}, location="view_args", as_kwargs=True
)
@use_args(
    {"forced": fields.Boolean(load_default=False)}, location="query", as_kwargs=True
)
@authenticated
def stop_server(user, forced, server_name):
    """
    Stop user server by name.

    ---
    delete:
      description: Stop a running server by name.
      parameters:
        - in: path
          schema:
            type: string
          name: server_name
          required: true
          description: The name of the server that should be deleted.
        - in: query
          schema:
            type: boolean
            default: false
          name: forced
          required: false
          description: |
            If true, delete immediately disregarding the grace period
            of the underlying JupyterServer resource.
      responses:
        204:
          description: The server was stopped successfully.
        404:
          description: The server cannot be found.
          content:
            application/json:
              schema: ErrorResponse
        500:
          description: The server exists but could not be successfully deleted.
          content:
            application/json:
              schema: ErrorResponse
      tags:
        - servers
    """
    config.k8s.client.delete_server(
        server_name, forced=forced, safe_username=user.safe_username
    )
    return "", 204


@bp.route("server_options", methods=["GET"])
@authenticated
def server_options(user):
    """
    Return a set of configurable server options.

    ---
    get:
      description: Get the options available to customize when starting a server.
      responses:
        200:
          description: Server options such as CPU, memory, storage, etc.
          content:
            application/json:
              schema: ServerOptionsEndpointResponse
      tags:
        - servers
    """
    # TODO: append image-specific options to the options json
    return ServerOptionsEndpointResponse().dump(
        {
            **config.server_options.ui_choices,
            "cloudstorage": {
                "s3": {"enabled": config.cloud_storage.s3.enabled},
                "azure_blob": {"enabled": config.cloud_storage.azure_blob.enabled},
            },
        },
    )


@bp.route("logs/<server_name>", methods=["GET"])
@use_args(
    {
        "max_lines": fields.Integer(
            load_default=250,
            validate=validate.Range(min=0, max=None, min_inclusive=True),
        )
    },
    as_kwargs=True,
    location="query",
)
@use_args(
    {"server_name": fields.Str(required=True)}, location="view_args", as_kwargs=True
)
@authenticated
def server_logs(user, max_lines, server_name):
    """
    Return the logs of the running server.

    ---
    get:
      description: Server logs.
      parameters:
        - in: path
          schema:
            type: string
          required: true
          name: server_name
          description: The name of the server whose logs should be fetched.
        - in: query
          schema:
            type: integer
            default: 250
            minimum: 0
          name: max_lines
          required: false
          description: |
            The maximum number of (most recent) lines to return from the logs.
      responses:
        200:
          description: Server logs. An array of strings where each element is a line of the logs.
          content:
            application/json:
              schema: ServerLogs
        404:
          description: The specified server does not exist.
          content:
            application/json:
              schema: ErrorResponse
      tags:
        - logs
    """
    logs = config.k8s.client.get_server_logs(
        server_name=server_name,
        max_log_lines=max_lines,
        safe_username=user.safe_username,
    )
    return jsonify(ServerLogs().dump(logs))


@bp.route("<path:namespace_project>/autosave", methods=["GET"])
@authenticated
def autosave_info(user, namespace_project):
    """
    Information about all autosaves for a project.

    ---
    get:
      description: Information about autosaved and recovered work from user sessions.
      parameters:
        - in: path
          name: namespace_project
          schema:
            type: string
          required: true
          description: |
            URL encoded namespace and project in the format of `namespace/project`.
            However since this should be URL encoded what should actually be used
            in the request is `namespace%2Fproject`.
      responses:
        200:
          description: All the autosave branches or PVs for the project
          content:
            application/json:
              schema: AutosavesList
        404:
          description: The requested project and/or namespace cannot be found
          content:
            application/json:
              schema: ErrorResponse
      tags:
        - autosave
    """
    if user.get_renku_project(namespace_project) is None:
        raise MissingResourceError(message=f"Cannot find project {namespace_project}")
    return jsonify(
        AutosavesList().dump(
            {
                "pvsSupport": config.sessions.storage.pvs_enabled,
                "autosaves": user.get_autosaves(namespace_project),
            },
        )
    )


@bp.route(
    "<path:namespace_project>/autosave/<path:autosave_name>",
    methods=["DELETE"],
)
@authenticated
def delete_autosave(user, namespace_project, autosave_name):
    """
    Delete an autosave PV and or branch.

    ---
    delete:
      description: Stop a running server by name.
      parameters:
        - in: path
          schema:
            type: string
          name: namespace_project
          required: true
          description: |
            URL encoded namespace and project in the format of `namespace/project`.
            However since this should be URL encoded what should actually be used
            in the request is `namespace%2Fproject`.
        - in: path
          schema:
            type: string
          name: autosave_name
          required: true
          description: |
            URL encoded name of the autosave as returned by the
            /<namespace_project>/autosave endpoint.
      responses:
        204:
          description: The autosave branch and/or PV has been deleted successfully.
        404:
          description: The requested project, namespace and/or autosave cannot be found.
          content:
            application/json:
              schema: ErrorResponse
      tags:
        - autosave
    """
    if user.get_renku_project(namespace_project) is None:
        raise MissingResourceError(message=f"Cannot find project {namespace_project}")
    autosave = AutosaveBranch.from_name(user, namespace_project, autosave_name)
    if not autosave:
        raise MissingResourceError(
            message=f"Cannot initialize or find the autosave {autosave_name}.",
            detail=(
                "This could be the result of a malformed autosave name or changing your username. "
                "If the problem persists you can always find all autosave branches in your "
                "Gitlab project."
            ),
        )
    autosave.delete()
    return make_response("", 204)


@bp.route("images", methods=["GET"])
@use_args({"image_url": fields.String(required=True)}, as_kwargs=True, location="query")
@authenticated
def check_docker_image(user, image_url):
    """
    Return the availability of the docker image.

    ---
    get:
      description: Docker image availability.
      parameters:
        - in: query
          schema:
            type: string
          required: true
          name: image_url
          description: The Docker image URL (tag included) that should be fetched.
      responses:
        200:
          description: The Docker image is available.
        404:
          description: The Docker image is not available.
      tags:
        - images
    """
    parsed_image = parse_image_name(image_url)
    if parsed_image is None:
        raise ImageParseError(
            f"The image {image_url} cannot be parsed, "
            "ensure you are providing a valid Docker image name."
        )
    token, _ = get_docker_token(**parsed_image, user=user)
    image_exists_result = image_exists(**parsed_image, token=token)
    if image_exists_result:
        return "", 200
    else:
        return "", 404
