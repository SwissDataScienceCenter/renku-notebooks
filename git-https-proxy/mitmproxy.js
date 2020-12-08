
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

const proxy = require('http-mitm-proxy')();
const url = require('url');

const proxyPort = process.env.MITM_PROXY_PORT || 8080;
const gitlabOauthToken = process.env.GITLAB_OAUTH_TOKEN;
const encodedCredentials = Buffer.from(
  `oauth2:${gitlabOauthToken}`
).toString('base64');
const repoUrl = new url.URL(process.env.REPOSITORY_URL);

let defaultPort;
switch (repoUrl.protocol) {
  case 'https:':
    defaultPort = 443;
  case 'http:':
    defaultport = 80;
}

proxy.onError(function(ctx, err) {
  /**
  * Simplest possible error handler.
  */
  console.error('proxy error:', err);
});


proxy.onRequest(function(ctx, callback) {
  /**
   * Request handler for the proxy. Checks if we're dealing with a
   * push/pull to/from the repo, if yes add the users GitLab oauth
   * token to the authorization header.
   */

  // A bit annoying that we have to reverse-engineer the request url here...
  let requestUrl = (
    `${ ctx.proxyToServerRequestOptions.agent.protocol }` +
    `//${ ctx.clientToProxyRequest.headers.host }` +
    `${ ctx.clientToProxyRequest.url }`
  )

  // Important: make sure that we're not adding the users token to a commit
  // to another git host, repo, etc.
  if (
    ctx.proxyToServerRequestOptions.agent.protocol === repoUrl.protocol &&
    ctx.proxyToServerRequestOptions.port === (repoUrl.port || defaultPort) &&
    ctx.proxyToServerRequestOptions.host === repoUrl.host &&
    ctx.proxyToServerRequestOptions.path.startsWith(repoUrl.pathname)
  ) {
    ctx.proxyToServerRequestOptions.headers['Authorization'] = `Basic ${encodedCredentials}`
    console.log(`Adding auth header to request: ${ requestUrl }`)
  } else {
    console.log(`Forwarding unmodified request: ${ requestUrl }`)
  }
  return callback();
});

proxy.listen({ port: proxyPort});
console.log(`Listening on port ${proxyPort}`);
