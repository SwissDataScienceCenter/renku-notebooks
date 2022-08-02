#!/bin/bash
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

set -e 
set -o pipefail

DEFAULT_NAMESPACE=$(kubectl config view --minify -o jsonpath='{..namespace}')
read -p "Enter the k9s namespace (default $DEFAULT_NAMESPACE): " NAMESPACE
[ -z "${NAMESPACE}" ] && NAMESPACE="$DEFAULT_NAMESPACE"
DEFAULT_HELM_RELEASE=$(helm list -a -n "$NAMESPACE" -f ".*renku.*" -q | head -1)
read -p "Enter the renku release name (default $DEFAULT_HELM_RELEASE): " HELM_RELEASE
[ -z "${HELM_RELEASE}" ] && HELM_RELEASE="$DEFAULT_HELM_RELEASE"
DEFAULT_PORT="8000"
read -p "Enter the port to forward to (default $DEFAULT_PORT): " PORT
[ -z "${PORT}" ] && PORT="$DEFAULT_PORT"

SERVICE_NAME="${HELM_RELEASE}-notebooks"
echo "Running command \"telepresence intercept -n $NAMESPACE $SERVICE_NAME --port $PORT\""
telepresence intercept -n $NAMESPACE $SERVICE_NAME --port $PORT
