FROM python:3.9-slim

LABEL maintainer="info@datascience.ch"

RUN apt-get update && \
    apt-get install -y --no-install-recommends git git-lfs netcat curl && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --disable-pip-version-check -U pip && \
    pip install --no-cache-dir --disable-pip-version-check pipenv

COPY Pipfile Pipfile.lock clone.sh rpc-server.py /app/
WORKDIR /app
RUN pipenv install --system --deploy

ENV HOST="0.0.0.0"
# Note: This will return a 200 as soon as the server is up,
#       even if this is an invalid rpc request.
HEALTHCHECK CMD curl http://$HOST:4000

ENTRYPOINT ["/app/clone.sh"]
CMD ["python", "/app/rpc-server.py"]
