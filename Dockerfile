FROM python:3.12.0a1-alpine as base
RUN apk add --no-cache curl tini && \
    adduser -u 1000 -g 1000 -D kyaku
WORKDIR /home/kyaku/renku-notebooks

FROM base as builder
ENV POETRY_HOME=/opt/poetry
COPY poetry.lock pyproject.toml ./
RUN apk add --no-cache alpine-sdk libffi-dev && \
    mkdir -p /opt/poetry && \
    curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.2.1 python3 - && \
    /opt/poetry/bin/poetry config virtualenvs.in-project true  && \
    /opt/poetry/bin/poetry config virtualenvs.options.no-setuptools true && \
    /opt/poetry/bin/poetry config virtualenvs.options.no-pip true  && \
    /opt/poetry/bin/poetry install --only main --no-root

FROM base as runtime
LABEL maintainer="info@datascience.ch"
USER 1000:1000
COPY --from=builder /home/kyaku/renku-notebooks/.venv .venv
COPY renku_notebooks renku_notebooks
COPY resource_schema_migrations resource_schema_migrations
ENTRYPOINT ["tini", "-g", "--"]
CMD [".venv/bin/gunicorn", "-b 0.0.0.0:8000", "renku_notebooks.wsgi:app", "-k gevent"]
