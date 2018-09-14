# Build as renku/singleuser
# Run with the DockerSpawner in JupyterHub

ARG JUPYTERHUB_VERSION=0.9.1
ARG BASE_IMAGE=jupyterhub/singleuser:$JUPYTERHUB_VERSION

FROM $BASE_IMAGE
ARG JUPYTERHUB_VERSION
ARG RENKU_VERSION=0.2.0rc1
MAINTAINER Swiss Data Science Center <info@datascience.ch>


ADD install /tmp/install

USER root
# Copied from jupyter-minimal-notebook
# Install all OS dependencies for fully functional notebook server
RUN apt-get update && apt-get install -yq --no-install-recommends \
    build-essential \
    curl \
    gnupg \
    git \
    libsm6 \
    libxext-dev \
    libxrender1 \
    lmodern \
    netcat \
    python-dev \
    unzip \
    nano \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash && sudo apt-get install git-lfs=2.4.2
USER $NB_USER

# install pinned jupyterhub and ensure notebook is installed
RUN python3 -m pip install -U pip && \
    python3 /tmp/install && \
    python3 -m pip install notebook jupyter_contrib_nbextensions widgetsnbextension && \
    jupyter contrib nbextension install --user

ADD setup.py gitlab_commit_push.py /tmp/gitlab_commit_push/
RUN python3 -m pip install /tmp/gitlab_commit_push/ && \
    jupyter serverextension enable --py gitlab_commit_push

ADD notebook.json /home/$NB_USER/.jupyter/nbconfig/
ADD gitlab-commit-push.js /home/$NB_USER/.local/share/jupyter/nbextensions/

# install renku-python
RUN conda create -y -n renku python=3.6 && \
    $CONDA_DIR/envs/renku/bin/pip install renku==$RENKU_VERSION && \
    echo "alias renku=$CONDA_DIR/envs/renku/bin/renku" >> /home/$NB_USER/.bashrc

COPY git-config.bashrc /home/$NB_USER/
RUN cat /home/$NB_USER/git-config.bashrc >> /home/$NB_USER/.bashrc && rm /home/$NB_USER/git-config.bashrc

# Add user `jovyan` to sudoers (passwordless)
USER root
RUN echo "$NB_USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
USER $NB_USER

CMD '/usr/local/bin/start-singleuser.sh'
