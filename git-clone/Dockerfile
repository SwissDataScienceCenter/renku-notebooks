ARG GIT_ALPINE_VERSION=1.0.17
ARG BASE_IMAGE=alpine/git:$GIT_ALPINE_VERSION
FROM $BASE_IMAGE

LABEL maintainer="Swiss Data Science Center <info@datascience.ch>"
RUN apk add --no-cache git-lfs bash curl tini

ENV USER_ID 1000
ENV GROUP_ID 100
ENV MOUNT_PATH /code

COPY clone.sh /clone.sh
WORKDIR /
ENTRYPOINT ["tini", "-g", "--"]
CMD ["bash", "/clone.sh"]
