FROM node:8.11.1 as react-builder

WORKDIR /app

COPY src/ui/package.json src/ui/package-lock.json /app/

RUN npm install --silent

COPY src/ui/public /app/public
COPY src/ui/src /app/src/

RUN npm run-script build


FROM python:3.6-alpine

MAINTAINER renku

RUN apk update && \
    apk add --no-cache curl && \
    pip install --no-cache-dir --disable-pip-version-check pipenv && \
    addgroup -g 1000 kyaku && \
    adduser -S -u 1000 -G kyaku kyaku

# Install all packages
COPY Pipfile Pipfile.lock /app/
WORKDIR /app
RUN pipenv install --system --deploy

# Move the service source code
COPY src /app/src
ENV FLASK_APP=/app/src/notebooks_service.py

# Copy static assets from react-builder stage
COPY --from=react-builder /app/build /app/static

# Switch to unpriviledged user
USER kyaku

CMD ["flask", "run", "-p" ,"8000", "-h", "0.0.0.0"]

HEALTHCHECK --interval=20s --timeout=10s --retries=5 CMD curl -f http://localhost:8000/health
