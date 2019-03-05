FROM jupyterhub/k8s-hub:0.9-174bbd5

USER root

COPY requirements-k8s.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt --no-cache-dir

COPY spawners.py /usr/local/lib/python3.6/dist-packages/

USER ${NB_USER}
