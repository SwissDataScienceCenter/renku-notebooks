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

from flask import jsonify, request, make_response
from kubernetes.client.rest import ApiException

from ...util.kubernetes_ import (
    read_namespaced_pod_log,
    get_user_server,
)
from ..auth import authenticated
from .blueprints import servers_bp


@servers_bp.route("logs/<server_name>")
@servers_bp.route("servers/<server_name>/logs")
@authenticated
def server_logs(user, server_name):
    """Return the logs of the running server."""
    server = get_user_server(user, server_name)
    if server:
        pod_name = server.get("state", {}).get("pod_name", "")
        try:
            max_lines = request.args.get("max_lines", default=250, type=int)
            logs = read_namespaced_pod_log(pod_name, max_lines)
        # catch predictable k8s api errors and return a significative string
        except ApiException as e:
            logs = ""
            if hasattr(e, "body"):
                k8s_error = json.loads(e.body)
                logs = f"Logs unavailable: {k8s_error['message']}"
        response = jsonify(str.splitlines(logs))
    else:
        response = make_response("", 404)
    return response
