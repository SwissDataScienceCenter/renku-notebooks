FROM python:3.11-bullseye as builder
RUN groupadd --gid 1000 renku && \
    adduser --gid 1000 --uid 1000 renku
USER 1000:1000
WORKDIR /app
RUN python3 -m pip install --user pipx && \
    python3 -m pipx ensurepath && \
    /home/renku/.local/bin/pipx install poetry
RUN /home/renku/.local/bin/poetry config virtualenvs.in-project true  && \
    /home/renku/.local/bin/poetry config virtualenvs.options.no-setuptools true && \
    /home/renku/.local/bin/poetry config virtualenvs.options.no-pip true
COPY poetry.lock pyproject.toml ./
RUN /home/renku/.local/bin/poetry install --only main --no-root


FROM python:3.11-slim-bullseye
RUN apt-get update && apt-get install -y \
    tini curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 1000 renku && \
    adduser --gid 1000 --uid 1000 renku
USER 1000:1000
WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY renku_notebooks renku_notebooks
COPY resource_schema_migrations resource_schema_migrations
ENTRYPOINT ["tini", "-g", "--"]
CMD [".venv/bin/gunicorn", "-b 0.0.0.0:8000", "renku_notebooks.wsgi:app", "-k gevent"]
