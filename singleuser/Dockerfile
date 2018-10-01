# Build as renku/singleuser
# Run with the DockerSpawner in JupyterHub

ARG JUPYTERHUB_VERSION=0.9
ARG BASE_IMAGE=jupyterhub/singleuser:$JUPYTERHUB_VERSION

FROM $BASE_IMAGE
ARG JUPYTERHUB_VERSION
ARG RENKU_VERSION=0.2.0rc1
MAINTAINER Swiss Data Science Center <info@datascience.ch>


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

# install jupyterlab, papermill, git extension and renku-jupyterlab-ts
RUN python3 -m pip install -U pip && \
    pip install -U jupyterlab papermill && \
    jupyter labextension update @jupyterlab/hub-extension --no-build && \
    jupyter labextension install @jupyterlab/git --no-build && \
    jupyter labextension install renku-jupyterlab-ts --no-build && \
    jupyter lab build && \
    jupyter labextension list && \
    python3 -m pip install -e git+https://github.com/jupyterlab/jupyterlab-git.git#egg=jupyterlab_git && \
    jupyter serverextension enable --py jupyterlab_git

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
