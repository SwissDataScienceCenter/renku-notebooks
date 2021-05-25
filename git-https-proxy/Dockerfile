FROM node:15-alpine3.12

LABEL maintainer="Swiss Data Science Center <info@datascience.ch>"

COPY package.json package-lock.json mitmproxy.js ./
RUN npm ci && npm cache clean --force

CMD ["node", "/mitmproxy.js"]
