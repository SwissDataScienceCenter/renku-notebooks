ARG K8S_HUB_VERSION=0.10.6
ARG BASE_IMAGE=jupyterhub/k8s-hub:$K8S_HUB_VERSION
FROM $BASE_IMAGE

USER root

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt --no-cache-dir

COPY spawners.py /usr/local/lib/python3.8/dist-packages/

USER ${NB_USER}
