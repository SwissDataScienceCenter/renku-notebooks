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

MINIKUBE_IP=`minikube ip`
CURRENT_CONTEXT=`kubectl config current-context`

echo "You are going to exchange k8s deployments using the following context: ${CURRENT_CONTEXT}"
read -p "Do you want to proceed? [y/n]"
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi
export JUPYTERHUB_BASE_URL=/jupyterhub/
export JUPYTERHUB_API_TOKEN=notebookstoken
export JUPYTERHUB_API_URL=http://${MINIKUBE_IP}${JUPYTERHUB_BASE_URL}hub/api
export JUPYTERHUB_SERVICE_PREFIX=${JUPYTERHUB_BASE_URL}services/notebooks/
export JUPYTERHUB_URL=http://${MINIKUBE_IP}/jupyterhub
export FLASK_APP=`pwd`/src/notebooks_service.py
export FLASK_DEBUG=1

telepresence --swap-deployment renku-notebooks --namespace renku --method inject-tcp --expose 8000:80 --run pipenv run flask run -p 8000 -h 0.0.0.0
