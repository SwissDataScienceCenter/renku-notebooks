FROM python:3.12-bookworm as builder
RUN groupadd --gid 1000 renku && \
    useradd --gid 1000 --uid 1000 --groups 100 --create-home jovyan && \
    mkdir -p /app && \
    chown -R 1000:1000 /app 
USER 1000:1000
WORKDIR /app
RUN python3 -m pip install --user pipx && \
    python3 -m pipx ensurepath && \
    /home/jovyan/.local/bin/pipx install poetry==1.8.5 && \
    python3 -m venv .venv
COPY poetry.lock pyproject.toml ./
RUN /home/jovyan/.local/bin/poetry export --only main --without-hashes -o requirements.txt && \
    .venv/bin/pip install -r requirements.txt --prefer-binary

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y \
    tini && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 1000 renku && \
    useradd --gid 1000 --uid 1000 --groups 100 --create-home jovyan && \
    mkdir -p /app && \
    chown -R 1000:1000 /app 
USER 1000:1000
WORKDIR /app
COPY --from=builder /app/.venv .venv
ADD secrets_mount ./secrets_mount 
ENTRYPOINT ["tini", "-g", "--"]
CMD [".venv/bin/python3", "-m", "secrets_mount"]

