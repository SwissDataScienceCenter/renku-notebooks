FROM python:3.7-slim

LABEL maintainer="info@datascience.ch"

RUN pip install --no-cache-dir --disable-pip-version-check -U pip && \
    pip install --no-cache-dir --disable-pip-version-check pipenv && \
    groupadd -g 1000 kyaku && \
    useradd -u 1000 -g kyaku kyaku --create-home --system && \
    groupadd -g 2000 debug

# Install all packages
COPY Pipfile Pipfile.lock /renku-notebooks/
WORKDIR /renku-notebooks
RUN pipenv install --system --deploy

COPY renku_notebooks /renku-notebooks/renku_notebooks
# Set group of code directory to 'debug' so files can be changed when running the pod
# in debug mode
RUN chown -R root:debug /renku-notebooks && chmod -R 775 /renku-notebooks
# Set up the flask app
ENV FLASK_APP=/renku-notebooks/renku-notebooks:create_app

# Switch to unpriviledged user
USER kyaku

CMD ["gunicorn", "-b 0.0.0.0:8000", "renku_notebooks.wsgi:app", "-k gevent"]

HEALTHCHECK --interval=20s --timeout=10s --retries=5 CMD curl -f http://localhost:8000/health
