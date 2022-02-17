# -*- coding: utf-8 -*-
#
# Copyright 2018 - Swiss Data Science Center (SDSC)
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
""" Notebooks service APIs """
from flask import Blueprint, Response

from .schemas import VersionResponse
from .. import config
from . import notebooks

bp = Blueprint("notebooks_service", __name__)


@bp.route("/health")
def health():
    """Just a health check path."""
    return Response("service running under {}".format(config.SERVICE_PREFIX))


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
    from ..version import __version__

    info = {
        "name": "renku-notebooks",
        "versions": [
            {
                "version": __version__,
                "data": {
                    "anonymous_sessions_enabled": config.ANONYMOUS_SESSIONS_ENABLED,
                    "s3_mount_enabled": config.S3_MOUNTS_ENABLED,
                },
            }
        ],
    }
    return VersionResponse().dump(info), 200


blueprints = [bp, notebooks.bp]
