FROM python:3.8-slim as base
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl tini && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1000 kyaku && \
    useradd -u 1000 -g kyaku -m kyaku
WORKDIR /home/kyaku/renku-notebooks

FROM base as builder
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_VIRTUALENVS_OPTIONS_NO_PIP=true
ENV POETRY_VIRTUALENVS_OPTIONS_NO_SETUPTOOLS=true
COPY poetry.lock pyproject.toml ./
RUN mkdir -p /opt/poetry && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    /opt/poetry/bin/poetry install --only main

FROM base as runtime
LABEL maintainer="info@datascience.ch"
USER 1000:1000
COPY --from=builder /home/kyaku/renku-notebooks/.venv .venv
COPY renku_notebooks renku_notebooks
COPY resource_schema_migrations resource_schema_migrations
ENTRYPOINT ["tini", "-g", "--"]
CMD [".venv/bin/gunicorn", "-b 0.0.0.0:8000", "renku_notebooks.wsgi:app", "-k gevent"]
