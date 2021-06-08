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
"""Authentication functions for the notebooks service."""

from functools import wraps
from flask import (
    Blueprint,
    jsonify,
    request,
    make_response,
    current_app,
)
from flask_apispec import doc, marshal_with

from .. import config
from .classes.user import User
from .schemas import UserSchema, JHUserInfo


bp = Blueprint("auth_bp", __name__, url_prefix=config.SERVICE_PREFIX)


def authenticated(f):
    """Decorator for authenticating with the Hub"""

    @wraps(f)
    def decorated(*args, **kwargs):
        user = User(request.headers)
        if user.logged_in:
            # the user is logged in
            return f(user, *args, **kwargs)
        else:
            # the user is not logged in
            response = jsonify(
                {"messages": {"error": "An authorization token is required."}}
            )
            response.status_code = 401
            return response

    return decorated

