FROM python:3.7-slim

LABEL maintainer="info@datascience.ch"

RUN pip install --no-cache-dir --disable-pip-version-check -U pip poetry && \
    groupadd -g 1000 kyaku && \
    useradd -u 1000 -g kyaku -m kyaku

# Switch to unpriviledged user
USER 1000:1000

# Install all packages
COPY poetry.lock pyproject.toml /home/kyaku/renku-notebooks/
WORKDIR /home/kyaku/renku-notebooks
RUN poetry install --no-dev

COPY renku_notebooks renku_notebooks
COPY resource_schema_migrations resource_schema_migrations
# Set up the flask app
ENV FLASK_APP=/home/kyaku/renku_notebooks/renku-notebooks:create_app

CMD ["poetry", "run", "gunicorn", "-b 0.0.0.0:8000", "renku_notebooks.wsgi:app", "-k gevent"]
