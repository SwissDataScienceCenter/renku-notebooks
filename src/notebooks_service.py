# -*- coding: utf-8 -*-
#
# Copyright 2018 - Swiss Data Science Center (SDSC)
# A partnership between École Polytechnique Fédérale de Lausanne (EPFL) and
# Eidgenössische Technische Hochschule Zürich (ETHZ).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Service creating named servers for given project."""

import hashlib
import json
import os
import string
import time
from urllib.parse import urljoin
from functools import partial, wraps

import docker
import escapism
import gitlab
import requests
from flask import Flask, Response, abort, make_response, redirect, request
from flask import jsonify
from flask import send_from_directory
from jupyterhub.services.auth import HubOAuth

SERVICE_PREFIX = os.environ.get('JUPYTERHUB_SERVICE_PREFIX', '/')
"""Service prefix is set by JupyterHub service spawner."""

auth = HubOAuth(
    api_token=os.environ['JUPYTERHUB_API_TOKEN'],
    cache_max_age=60,
    oauth_client_id=os.getenv(
        'NOTEBOOKS_OAUTH_CLIENT_ID', 'service-notebooks'
    ),
)
"""Wrap JupyterHub authentication service API."""

app = Flask(__name__)


def _server_name(namespace, project, commit_sha):
    """Form a DNS-safe server name."""
    escape = partial(
        escapism.escape,
        safe=set(string.ascii_lowercase + string.digits),
        escape_char='-',
    )
    return '{namespace}-{project}-{commit_sha}'.format(
        namespace=escape(namespace)[:10],
        project=escape(project)[:10],
        commit_sha=commit_sha[:7]
    ).lower()


def authenticated(f):
    """Decorator for authenticating with the Hub"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get(auth.cookie_name)
        if token:
            user = auth.user_for_token(token)
        else:
            user = None
        if user:
            return f(user, *args, **kwargs)
        else:
            # redirect to login url on failed auth
            state = auth.generate_state(next_url=request.path)
            response = make_response(
                redirect(auth.login_url + '&state=%s' % state)
            )
            response.set_cookie(auth.state_cookie_name, state)
            return response

    return decorated


@app.route('/health')
def health():
    """Just a health check path."""
    return Response('service running under {}'.format(SERVICE_PREFIX))


@app.route(SERVICE_PREFIX)
@authenticated
def whoami(user):
    """Return information about the authenticated user."""
    headers = {auth.auth_header_name: 'token {0}'.format(auth.api_token)}
    info = json.loads(
        requests.request(
            'GET',
            '{prefix}/users/{user[name]}'.format(
                prefix=auth.api_url, user=user
            ),
            headers=headers
        ).text
    )
    return jsonify(info)


@authenticated
@app.route(urljoin(SERVICE_PREFIX, 'ui/'), defaults={'path': ''})
@app.route(urljoin(SERVICE_PREFIX, 'ui/<path:path>'), methods=['GET'])
def ui(path):
    """Route for serving a UI for managing running servers."""
    if not path:
        path = "index.html"
    return send_from_directory('../static', filename=path)
    # Use this varient for development
    # return send_from_directory('ui/build', filename=path)


@app.route(
    urljoin(SERVICE_PREFIX, '<namespace>/<project>/<commit_sha>'),
    methods=['GET']
)
@app.route(
    urljoin(
        SERVICE_PREFIX, '<namespace>/<project>/<commit_sha>/<path:notebook>'
    ),
    methods=['GET']
)
@authenticated
def launch_notebook(user, namespace, project, commit_sha, notebook=None):
    """Launch user server with a given name."""
    server_name = _server_name(namespace, project, commit_sha)

    headers = {auth.auth_header_name: 'token {0}'.format(auth.api_token)}

    # 1. launch using spawner that checks the access
    r = requests.request(
        'POST',
        '{prefix}/users/{user[name]}/servers/{server_name}'.format(
            prefix=auth.api_url, user=user, server_name=server_name
        ),
        json={
            'branch': request.args.get('branch', 'master'),
            'commit_sha': commit_sha,
            'namespace': namespace,
            'notebook': notebook,
            'project': project,
        },
        headers=headers,
    )

    notebook_url = urljoin(
        os.environ.get('JUPYTERHUB_BASE_URL'),
        'user/{user[name]}/{server_name}/'.format(
            user=user, server_name=server_name
        )
    )

    if notebook:
        notebook_url += '/notebooks/{notebook}'.format(notebook=notebook)

    # 2. redirect to the server when ready
    if r.status_code == 201:
        # server is already running
        return redirect(notebook_url)

    elif r.status_code == 202:
        # server is spawning - wait a max of 900 seconds = 15 minutes
        app.logger.debug('waiting for server {}'.format(server_name))
        tstart = time.time()
        while time.time() - tstart < 900:
            if server_name in json.loads(
                requests.request(
                    'GET',
                    '{prefix}/users/{user[name]}'.format(
                        prefix=auth.api_url, user=user
                    ),
                    headers=headers
                ).text
            )['servers']:
                app.logger.debug(
                    'server {} started - redirecting'.format(server_name)
                )
                return redirect(notebook_url)
            else:
                time.sleep(2)
        abort(404)
    abort(r.status_code)


@app.route(
    urljoin(SERVICE_PREFIX, '<namespace>/<project>/<commit_sha>'),
    methods=['DELETE']
)
@authenticated
def stop_notebook(user, namespace, project, commit_sha):
    """Stop user server with name."""
    server_name = _server_name(namespace, project, commit_sha)
    headers = {'Authorization': 'token %s' % auth.api_token}

    r = requests.request(
        'DELETE',
        '{prefix}/users/{user[name]}/servers/{server_name}'.format(
            prefix=auth.api_url, user=user, server_name=server_name
        ),
        headers=headers
    )
    return app.response_class(r.content, status=r.status_code)


@app.route(
    urljoin(SERVICE_PREFIX, 'stop/<server_name>'),
    methods=['DELETE']
)
@authenticated
def stop_server(user, server_name):
    """Stop user server with name."""
    headers = {'Authorization': 'token %s' % auth.api_token}

    r = requests.request(
        'DELETE',
        '{prefix}/users/{user[name]}/servers/{server_name}'.format(
            prefix=auth.api_url, user=user, server_name=server_name
        ),
        headers=headers
    )
    return app.response_class(r.content, status=r.status_code)


@app.route(urljoin(SERVICE_PREFIX, 'oauth_callback'))
def oauth_callback():
    """Set a token in the cookie."""
    code = request.args.get('code', None)
    if code is None:
        abort(403)

    # validate state field
    arg_state = request.args.get('state', None)
    cookie_state = request.cookies.get(auth.state_cookie_name)
    if arg_state is None or arg_state != cookie_state:
        # state doesn't match
        abort(403)

    token = auth.token_for_code(code)
    next_url = auth.get_next_url(cookie_state) or SERVICE_PREFIX
    response = make_response(redirect(next_url))
    response.set_cookie(auth.cookie_name, token)
    return response
