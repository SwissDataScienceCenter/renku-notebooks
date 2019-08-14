#!/bin/sh

wget -q ${HELM_URL}/${HELM_TGZ} -O ${TEMP_DIR}/${HELM_TGZ}
tar -C ${TEMP_DIR} -xzv -f ${TEMP_DIR}/${HELM_TGZ}
PATH=${TEMP_DIR}/linux-amd64/:$PATH
helm init --client-only
helm repo add jupyterhub https://jupyterhub.github.io/helm-chart
helm dependency update helm-chart/renku-notebooks
