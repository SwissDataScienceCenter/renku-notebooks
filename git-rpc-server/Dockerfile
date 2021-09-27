FROM python:3.9-slim

LABEL maintainer="info@datascience.ch"

RUN apt-get update && \
    apt-get install -y --no-install-recommends git git-lfs && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --disable-pip-version-check -U pip && \
    pip install --no-cache-dir --disable-pip-version-check pipenv

COPY Pipfile Pipfile.lock /app/
COPY git_rpc_server/ /app/git_rpc_server/
RUN cd /app && pipenv install --system --deploy

ENV HOST="0.0.0.0"
ENV PYTHONPATH="/app:${PYTHONPATH}"
# Note: This will return a 200 as soon as the server is up,
#       even if this is an invalid rpc request.
HEALTHCHECK CMD curl http://$HOST:4000

ENTRYPOINT ["python", "-m"]
CMD ["git_rpc_server.run"]
