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
from functools import partial, wraps
from urllib.parse import urljoin, urlparse, urlunparse

import docker
import escapism
import gitlab
import requests
from flask import (
    Flask, Response, abort, jsonify, make_response, redirect, render_template,
    request, send_file, send_from_directory
)
from jupyterhub.services.auth import HubOAuth

SERVICE_PREFIX = os.environ.get('JUPYTERHUB_SERVICE_PREFIX', '/')
"""Service prefix is set by JupyterHub service spawner."""

ANNOTATION_PREFIX = 'hub.jupyter.org'
"""The prefix used for annotations by the KubeSpawner."""

GITLAB_URL = os.environ.get('GITLAB_URL', 'https://gitlab.com')
"""The GitLab instance to use."""

IMAGE_REGISTRY = os.environ.get('IMAGE_REGISTRY', '')
"""The default image registry."""

SERVER_STATUS_MAP = {'spawn': 'spawning', 'stop': 'stopping'}

# check if we are running on k8s
try:
    from kubernetes import client, config
    config.load_incluster_config()
    with open(
        '/var/run/secrets/kubernetes.io/serviceaccount/namespace', 'rt'
    ) as f:
        kubernetes_namespace = f.read()
    KUBERNETES = True
except (config.ConfigException, FileNotFoundError):
    KUBERNETES = False

auth = HubOAuth(
    api_token=os.environ['JUPYTERHUB_API_TOKEN'],
    cache_max_age=60,
)
"""Wrap JupyterHub authentication service API."""


# From: http://flask.pocoo.org/snippets/35/
class ReverseProxied(object):
    """Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    :param app: the WSGI application
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


app = Flask(__name__)
app.wsgi_app = ReverseProxied(app.wsgi_app)


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


def _notebook_url(user, server_name, notebook=None):
    """Form the notebook server URL."""
    notebook_url = urljoin(
        os.environ.get('JUPYTERHUB_BASE_URL'),
        'user/{user[name]}/{server_name}/'.format(
            user=user, server_name=server_name
        )
    )
    if notebook:
        notebook_url += 'lab/tree/{notebook}'.format(notebook=notebook)
    return notebook_url


def authenticated(f):
    """Decorator for authenticating with the Hub"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get(
            auth.cookie_name
        ) or request.headers.get('Authorization', 'token').split('token',
                                                                 1)[1].strip()
        if token:
            user = auth.user_for_token(token)
        else:
            user = None
        if user:
            return f(user, *args, **kwargs)
        else:
            # redirect to login url on failed auth
            state = auth.generate_state(next_url=request.path)
            app.logger.debug(
                'Auth flow, redirecting to: {}'.format(auth.login_url)
            )
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


@authenticated
@app.route(SERVICE_PREFIX, methods=['GET'])
@app.route(urljoin(SERVICE_PREFIX, 'index.html'), methods=['GET'])
def root():
    """Route for serving a UI for managing running servers."""
    return redirect(urljoin(SERVICE_PREFIX, 'ui/'))


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


@app.route(urljoin(SERVICE_PREFIX, 'user'))
@authenticated
def whoami(user):
    """Return information about the authenticated user."""
    info = get_user_info(user)
    return jsonify(info)


def get_user_info(user):
    """Return the full user object."""
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

    return info


def get_gitlab_project(user, namespace, project):
    """Retrieve the GitLab project."""
    info = get_user_info(user)
    auth_state = info.get('auth_state')
    assert auth_state

    gl = gitlab.Gitlab(
        GITLAB_URL, api_version=4, oauth_token=auth_state['access_token']
    )

    try:
        gl.auth()
        gl_project = gl.projects.get('{0}/{1}'.format(namespace, project))
        gl_user = gl.user
        app.logger.info('Got user profile: {}'.format(gl_user))

        # gather project permissions for the logged in user
        permissions = gl_project.attributes['permissions']
        access_level = max([
            x[1].get('access_level', 0) for x in permissions.items() if x[1]
        ])
        app.logger.debug(
            'access level for user {username} in '
            '{namespace}/{project} = {access_level}'.format(
                username=user.get('name'),
                namespace=namespace,
                project=project,
                access_level=access_level
            )
        )
    except Exception as e:
        app.logger.error(e)
        return app.response_class(
            status=500, response='There was a problem accessing the project.'
        )

    if access_level < gitlab.DEVELOPER_ACCESS:
        return app.response_class(
            status=401, response='Not authorized to view project.'
        )

    return gl_project


def get_job_status(pipeline, job_name):
    """Helper method to retrieve job status based on the job name."""
    status = [
        job.attributes['status']
        for job in pipeline.jobs.list() if job.attributes['name'] == job_name
    ]
    return status.pop() if status else None


def get_notebook_image(user, namespace, project, commit_sha):
    """Check if the image for the namespace/project/commit_sha is ready."""
    gl_project = get_gitlab_project(user, namespace, project)

    # image build timeout -- configurable, defaults to 10 minutes
    image_build_timeout = int(os.getenv('IMAGE_BUILD_TIMEOUT', 600))

    image = os.getenv('NOTEBOOKS_DEFAULT_IMAGE', 'renku/singleuser:latest')

    commit_sha_7 = commit_sha[:7]

    for pipeline in gl_project.pipelines.list():
        if pipeline.attributes['sha'] == commit_sha:
            status = get_job_status(pipeline, 'image_build')

            if not status:
                # there is no image_build job for this commit
                # so we use the default image
                app.logger.info('No image_build job found in pipeline.')

            # we have an image_build job in the pipeline, check status
            elif status == 'success':
                # the image was built
                # it *should* be there so lets use it
                image = '{image_registry}/{namespace}'\
                        '/{project}:{commit_sha_7}'.format(
                                image_registry=IMAGE_REGISTRY,
                                commit_sha_7=commit_sha_7,
                                namespace=namespace,
                                project=project
                        ).lower()
                app.logger.info(f'Using image {image}.')

            else:
                app.logger.info(
                    'No image found for project {0} commit {1} - '
                    'using {2} instead'.format(project, commit_sha, image)
                )
            break

    return image


def get_user_server(user, server_name):
    """Fetch the user named server"""
    headers = {auth.auth_header_name: 'token {0}'.format(auth.api_token)}
    user_info = requests.request(
        'GET',
        '{prefix}/users/{user[name]}'.format(prefix=auth.api_url, user=user),
        headers=headers
    ).json()

    servers = user_info.get('servers', {})
    server = servers.get(server_name, {})
    app.logger.debug(server)
    return server


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
def notebook_status(user, namespace, project, commit_sha, notebook=None):
    """Returns the current status of a user named server or redirect to it if running"""
    server_name = _server_name(namespace, project, commit_sha)
    notebook_url = _notebook_url(user, server_name, notebook)

    server = get_user_server(user, server_name)
    status = SERVER_STATUS_MAP.get(server.get('pending'), 'not found')

    app.logger.debug(f'server {server_name}: {status}')

    # if we just want the server json, return here
    if request.environ['HTTP_ACCEPT'] == 'application/json':
        return jsonify(server)

    # if html was requested, check for status and redirect as appropriate
    if server.get('ready'):
        return redirect(notebook_url)

    return render_template(
        'server_status.html',
        namespace=namespace,
        project=project,
        commit_sha=commit_sha[:7],
        server_name=server_name,
        status=status,
    )


@app.route(
    urljoin(SERVICE_PREFIX, '<namespace>/<project>/<commit_sha>'),
    methods=['POST']
)
@app.route(
    urljoin(
        SERVICE_PREFIX, '<namespace>/<project>/<commit_sha>/<path:notebook>'
    ),
    methods=['POST']
)
@authenticated
def launch_notebook(user, namespace, project, commit_sha, notebook=None):
    """Launch user server with a given name."""
    server_name = _server_name(namespace, project, commit_sha)

    # 0. check if server already exists and if so return it
    server = get_user_server(user, server_name)
    if server:
        return app.response_class(
            response=json.dumps(server),
            status=200,
            mimetype='application/json'
        )

    ## 1. launch using spawner that checks the access
    headers = {auth.auth_header_name: 'token {0}'.format(auth.api_token)}

    # set the notebook image
    image = get_notebook_image(user, namespace, project, commit_sha)

    ## process the server options
    # server options from system configuration
    server_options_file = os.getenv(
        'NOTEBOOKS_SERVER_OPTIONS_PATH',
        '/etc/renku-notebooks/server_options.json'
    )

    with open(server_options_file) as f:
        server_options_defaults = json.load(f)

    # process the requested options and set others to defaults from config
    server_options = (request.get_json() or {}).get('serverOptions', {})
    server_options.setdefault(
        'defaultUrl',
        server_options_defaults.pop('defaultUrl', {}).get(
            'default', os.getenv('JUPYTERHUB_SINGLEUSER_DEFAULT_URL')
        )
    )

    for key in server_options_defaults.keys():
        server_options.setdefault(
            key,
            server_options_defaults.get(key)['default']
        )

    payload = {
        'branch': request.args.get('branch', 'master'),
        'commit_sha': commit_sha,
        'namespace': namespace,
        'notebook': notebook,
        'project': project,
        'image': image,
        'git_clone_image': os.getenv('GIT_CLONE_IMAGE', 'renku/git-clone:latest'),
        'server_options': server_options,
    }
    app.logger.debug(payload)

    if os.environ.get('GITLAB_REGISTRY_SECRET'):
        payload['image_pull_secrets'] = payload.get('image_pull_secrets', [])
        payload['image_pull_secrets'].append(
            os.environ['GITLAB_REGISTRY_SECRET']
        )

    r = requests.request(
        'POST',
        '{prefix}/users/{user[name]}/servers/{server_name}'.format(
            prefix=auth.api_url,
            user=user,
            server_name=server_name,
            image=image
        ),
        json=payload,
        headers=headers,
    )

    # 2. check response, we expect:
    #   - HTTP 201 if the server is already running; in this case redirect to it
    #   - HTTP 202 if the server is spawning
    if r.status_code == 201:
        app.logger.debug(
            'server {server_name} already running'.format(
                server_name=server_name
            )
        )
    elif r.status_code == 202:
        app.logger.debug(
            'spawn initialized for {server_name}'.format(
                server_name=server_name
            )
        )
    elif r.status_code == 400:
        app.logger.debug('server in pending state')
    else:
        # unexpected status code, abort
        abort(r.status_code)

    # fetch the server from JupyterHub
    server = get_user_server(user, server_name)
    return app.response_class(
        response=json.dumps(server),
        status=r.status_code,
        mimetype='application/json'
    )


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
    urljoin(
        SERVICE_PREFIX, '<namespace>/<project>/<commit_sha>/server_options'
    ),
    methods=['GET']
)
@authenticated
def server_options(user, namespace, project, commit_sha):
    """Return a set of configurable server options."""
    server_options_file = os.getenv(
        'NOTEBOOKS_SERVER_OPTIONS_PATH',
        '/etc/renku-notebooks/server_options.json'
    )
    with open(server_options_file) as f:
        server_options = json.load(f)

    ## TODO: append image-specific options to the options json
    return jsonify(server_options)


@app.route(
    urljoin(SERVICE_PREFIX, 'servers/<server_name>'), methods=['DELETE']
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


# Define /pods only if we are running in a k8s pod
if KUBERNETES:

    @app.route(urljoin(SERVICE_PREFIX, 'pods'), methods=['GET'])
    @authenticated
    def list_pods(user):
        pods = get_pods()
        return jsonify(pods.to_dict())

    app.logger.info('Providing GET /pods endpoint')

    def get_pods():
        """Get the running pods."""
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(
            kubernetes_namespace, label_selector='heritage = jupyterhub'
        )
        return pods
else:
    app.logger.info('Cannot provide GET /pods endpoint')


def get_notebook_container_status(username, server_name):
    """Get the status of the specified pod."""
    status = 'not running'
    if KUBERNETES:
        pods = get_pods()
        for pod in pods.items:
            # find the pod matching username and server name
            annotations = pod.metadata.annotations
            if (
                annotations.get('{}/servername'.format(ANNOTATION_PREFIX)
                                ) == server_name
            ) and (
                annotations.get('{}/username'.format(ANNOTATION_PREFIX)
                                ) == username
            ):
                container_statuses = pod.status.container_statuses
                if container_statuses:
                    for c in container_statuses:
                        if c.name == 'notebook':
                            # get the non-null state value
                            status = [
                                i[0] for i in c.state.to_dict().items() if i[1]
                            ][0]
    return status
