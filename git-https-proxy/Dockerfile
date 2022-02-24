FROM node:15.14-alpine3.12

LABEL maintainer="Swiss Data Science Center <info@datascience.ch>"

COPY package.json package-lock.json mitmproxy.js ./
RUN npm ci && npm cache clean --force && apk add --no-cache tini

ENTRYPOINT ["tini", "-g", "--"]
CMD ["node", "--use-openssl-ca", "/mitmproxy.js"]
