
/*!
 * Copyright 2020 - Swiss Data Science Center (SDSC)
 * A partnership between École Polytechnique Fédérale de Lausanne (EPFL) and
 * Eidgenössische Technische Hochschule Zürich (ETHZ).
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const http = require('http');
const proxy = require('http-mitm-proxy')();
const url = require('url');

const proxyPort = process.env.MITM_PROXY_PORT || 8080;
const healthPort = process.env.HEALTH_PORT || 8081;
const anonymousSession = process.env.ANONYMOUS_SESSION === "true";
const gitlabOauthToken = process.env.GITLAB_OAUTH_TOKEN;
const encodedCredentials = Buffer.from(`oauth2:${gitlabOauthToken}`)
  .toString('base64');
const repoUrl = new url.URL(process.env.REPOSITORY_URL);

let defaultPort;
switch (repoUrl.protocol) {
  case 'https:':
    defaultPort = 443;
    break;
  case 'http:':
    defaultPort = 80;
    break;
  default:
    defaultPort = undefined;
    break;
}

proxy.onError(function (ctx, err) {
  /**
  * Simple error handler. Note that recent git versions close the
  * connection to the proxy unexpectedly. This results in a proxy
  * error which we can safely ignore.
  */

  if (err.code !== 'ECONNRESET') {
    console.error('proxy error:', err);
    console.error('error request context:', ctx);
  }
});


proxy.onRequest(function (ctx, callback) {
  /**
   * Request handler for the proxy. Checks if we're dealing with a
   * push/pull to/from the repo, if yes add the users GitLab oauth
   * token to the authorization header.
   */

  // A bit annoying that we have to reverse-engineer the request url here...
  const requestUrl =
    `${ctx.proxyToServerRequestOptions.agent.protocol}//` +
    ctx.clientToProxyRequest.headers.host +
    ctx.clientToProxyRequest.url;


  const validGitRequest = ctx.proxyToServerRequestOptions.agent.protocol === repoUrl.protocol &&
    ctx.proxyToServerRequestOptions.port === (repoUrl.port || defaultPort) &&
    ctx.proxyToServerRequestOptions.host === repoUrl.host

  if (anonymousSession) {
    console.log(`Anonymous session, not adding auth headers, letting request through without adding auth headers.`);
    return callback();
  }

  if (!validGitRequest) {
    console.log(`The request is not for the git repository, letting request through without adding auth headers`);
    return callback();
  }

  // User is not anonymous and request is for the git repository.
  // Important: make sure that we're not adding the users token to a commit
  // to another git host, repo, etc.
  console.log(`Adding auth header to request: ${requestUrl}`);
  ctx.proxyToServerRequestOptions.headers['Authorization'] =
    `Basic ${encodedCredentials}`;
  return callback();

});

proxy.listen({ port: proxyPort });
console.log(`Proxy listening on port ${proxyPort}`);

var healthServer = http.createServer(function (req, res) {
  if (req.url == '/health') {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.write('Up and running...');
    res.end();
  }
});

healthServer.listen(healthPort);
console.log(`Healthcheck listening on port ${healthPort} under /health`)
