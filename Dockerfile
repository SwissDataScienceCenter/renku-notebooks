FROM python:3.7-alpine

LABEL maintainer="info@datascience.ch"

RUN apk update && \
    apk add --no-cache curl build-base libffi-dev openssl-dev && \
    pip install --no-cache-dir --disable-pip-version-check -U pip && \
    pip install --no-cache-dir --disable-pip-version-check pipenv && \
    addgroup -g 1000 kyaku && \
    adduser -S -u 1000 -G kyaku kyaku

# Install all packages
COPY Pipfile Pipfile.lock /renku-notebooks/
WORKDIR /renku-notebooks
RUN pipenv install --system --deploy

COPY renku_notebooks /renku-notebooks/renku_notebooks
# Set up the flask app
ENV FLASK_APP=/renku-notebooks/renku-notebooks:create_app

# Switch to unpriviledged user
USER kyaku

CMD ["gunicorn", "-b 0.0.0.0:8000", "renku_notebooks.wsgi:app", "-k gevent"]

HEALTHCHECK --interval=20s --timeout=10s --retries=5 CMD curl -f http://localhost:8000/health
