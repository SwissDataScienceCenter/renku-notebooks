ARG GIT_ALPINE_VERSION=1.0.7
ARG BASE_IMAGE=alpine/git:$GIT_ALPINE_VERSION
FROM $BASE_IMAGE

LABEL maintainer="Swiss Data Science Center <info@datascience.ch>"
RUN apk update && apk add git-lfs bash

ENV USER_ID 1000
ENV GROUP_ID 100
ENV MOUNT_PATH /code

COPY entrypoint.sh /entrypoint.sh

WORKDIR ${MOUNT_PATH}

ENTRYPOINT /entrypoint.sh
