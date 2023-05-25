FROM python:3.11-bullseye as builder
RUN groupadd --gid 1000 renku && \
    useradd --gid 1000 --uid 1000 --groups 100 --create-home renku && \
    mkdir -p /app && \
    chown -R 1000:1000 /app 
USER 1000:1000
WORKDIR /app
RUN python3 -m pip install --user pipx && \
    python3 -m pipx ensurepath && \
    /home/renku/.local/bin/pipx install poetry && \
    python3 -m venv .venv
COPY poetry.lock pyproject.toml ./
RUN /home/renku/.local/bin/poetry export --only main --without-hashes -o requirements.txt && \
    .venv/bin/pip install -r requirements.txt --prefer-binary

FROM python:3.11-slim-bullseye
RUN apt-get update && apt-get install -y \
    tini && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 1000 renku && \
    useradd --gid 1000 --uid 1000 --groups 100 --create-home renku && \
    mkdir -p /app && \
    chown -R 1000:1000 /app 
USER 1000:1000
WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY renku_notebooks renku_notebooks
COPY resource_schema_migrations resource_schema_migrations
ENTRYPOINT ["tini", "-g", "--"]
CMD [".venv/bin/gunicorn", "-b 0.0.0.0:8000", "renku_notebooks.wsgi:app", "-k gevent"]
