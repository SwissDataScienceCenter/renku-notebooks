FROM python:3.7-alpine

LABEL maintainer="info@datascience.ch"

RUN apk update && \
    apk add --no-cache curl build-base libffi-dev openssl-dev && \
    pip install --no-cache-dir --disable-pip-version-check -U pip && \
    pip install --no-cache-dir --disable-pip-version-check pipenv

# Install all packages
COPY Pipfile Pipfile.lock /clean_user_registry_secrets/
WORKDIR /clean_user_registry_secrets
RUN pipenv install --system --deploy

COPY clean_user_registry_secrets.py /clean_user_registry_secrets/

CMD ["python", "clean_user_registry_secrets.py"]
