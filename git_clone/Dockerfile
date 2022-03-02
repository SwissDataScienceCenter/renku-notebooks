ARG GIT_ALPINE_VERSION=1.0.17
ARG BASE_IMAGE=alpine/git:$GIT_ALPINE_VERSION
FROM $BASE_IMAGE

LABEL maintainer="Swiss Data Science Center <info@datascience.ch>"

RUN apk add --no-cache python3 py3-pip git-lfs && \
    pip install --no-cache-dir --disable-pip-version-check -U pip && \
    pip install --no-cache-dir --disable-pip-version-check --ignore-installed distlib pipenv

ENV USER_ID 1000
ENV GROUP_ID 100
ENV MOUNT_PATH /code

ADD . /git-clone/
WORKDIR /git-clone
RUN pipenv install --system --deploy

ENTRYPOINT ["pipenv", "run", "python", "clone.py"]
