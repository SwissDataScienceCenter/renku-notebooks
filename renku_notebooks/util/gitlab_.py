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
"""Integrating interactive environments with GitLab."""
import gitlab


def check_user_has_developer_permission(gl_project):
    return _get_project_permissions(gl_project) >= gitlab.DEVELOPER_ACCESS


def _get_project_permissions(gl_project):
    """Return the user's access level for the given project."""
    permissions = gl_project.attributes["permissions"]
    access_level = max(
        [x[1].get("access_level", 0) for x in permissions.items() if x[1]]
    )
    return access_level
