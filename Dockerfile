FROM python:3.7-slim

LABEL maintainer="info@datascience.ch"

RUN pip install --no-cache-dir --disable-pip-version-check -U pip && \
    pip install --no-cache-dir --disable-pip-version-check pipenv && \
    pip install --no-cache-dir --disable-pip-version-check yamlpath && \
    groupadd -g 1000 kyaku && \
    useradd -u 1000 -g kyaku kyaku

# Install all packages
COPY Pipfile Pipfile.lock /renku-notebooks/
WORKDIR /renku-notebooks
RUN pipenv install --system --deploy

COPY renku_notebooks /renku-notebooks/renku_notebooks
COPY resource_schema_migrations /resource_schema_migrations
# Set up the flask app
ENV FLASK_APP=/renku-notebooks/renku-notebooks:create_app

# Update version
COPY helm-chart/renku-notebooks/Chart.yaml /renku-notebooks/
RUN echo "__version__ = \"$(yaml-get --query .version Chart.yaml)\"" > renku_notebooks/version.py

# Switch to unpriviledged user
USER kyaku

CMD ["gunicorn", "-b 0.0.0.0:8000", "renku_notebooks.wsgi:app", "-k gevent"]

HEALTHCHECK --interval=20s --timeout=10s --retries=5 CMD curl -f http://localhost:8000/health
