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

CURRENT_CONTEXT=`kubectl config current-context`

if [[ $CURRENT_CONTEXT == 'minikube' ]]
then
  echo "Exchanging k8s deployments using the following context: ${CURRENT_CONTEXT}"
  SERVICE_NAME=renku-notebooks
  DEV_NAMESPACE=renku
else
  echo "You are going to exchange k8s deployments using the following context: ${CURRENT_CONTEXT}"
  read -p "Do you want to proceed? [y/n]"
  if [[ ! $REPLY =~ ^[Yy]$ ]]
  then
      exit 1
  fi

  if [[ ! $DEV_NAMESPACE ]]
  then
    read -p "enter your k8s namespace: "
    DEV_NAMESPACE=$REPLY
  fi
  SERVICE_NAME=${DEV_NAMESPACE}-renku-notebooks
fi

: ${DEV_NAMESPACE:-renku}
: ${JUPYTERHUB_API_TOKEN:-notebookstoken}
: ${JUPYTERHUB_BASE_URL:-/jupyterhub/}
: ${JUPYTERHUB_URL:-http://${MINIKUBE_IP}{JUPYTERHUB_BASE_URL}}
: ${JUPYTERHUB_API_URL:-http://${JUPYTERHUB_URL}hub/api}
: ${JUPYTERHUB_SERVICE_PREFIX:-${JUPYTERHUB_BASE_URL}services/notebooks/}

export JUPYTERHUB_BASE_URL
export JUPYTERHUB_API_TOKEN
export JUPYTERHUB_API_URL
export JUPYTERHUB_SERVICE_PREFIX
export JUPYTERHUB_URL
export FLASK_APP=`pwd`/renku_notebooks/wsgi.py
export FLASK_DEBUG=0
export NOTEBOOKS_SERVER_OPTIONS_DEFAULTS_PATH=`pwd`/tests/dummy_server_defaults.json
export NOTEBOOKS_SERVER_OPTIONS_UI_PATH=`pwd`/tests/dummy_server_options.json

echo ""
echo "================================================================================================================="
echo -e "Ready to start coding? \U1F680 \U1F916"
echo "Once telepresence has started, copy-paste the following command to start the development server:"
echo "> pipenv run flask run -p 8000 -h 0.0.0.0"
echo ""
echo "Or use the following to run in the VS Code debugger:"
echo "> VSCODE_DEBUG=1 pipenv run flask run -p 8000 -h 0.0.0.0 --no-reload"
echo "================================================================================================================="
echo ""

if [[ "$OSTYPE" == "linux-gnu" ]]
then
  TELEPRESENCE_USE_DEPLOYMENT=1 telepresence --swap-deployment ${SERVICE_NAME} --namespace ${DEV_NAMESPACE} --expose 8000:80  --run-shell
else
  TELEPRESENCE_USE_DEPLOYMENT=1 telepresence --swap-deployment ${SERVICE_NAME} --namespace ${DEV_NAMESPACE} --method inject-tcp --expose 8000:80  --run-shell
fi
