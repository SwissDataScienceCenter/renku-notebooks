import os
from functools import partial
from urllib.parse import urljoin

from flask import Flask
from jsonrpc.backend.flask import api, Blueprint

from git_services.sidecar.rpc_server import autosave, status, renku
from git_services.sidecar.config import config_from_env


def health_endpoint():
    """Health endpoint for probes."""
    return {"status": "running"}


def get_app():
    """Setup flask app"""
    os.environ["RUNNING_WITH_GEVENT"] = "true"
    config = config_from_env()
    app = Flask(__name__)
    health_bp = Blueprint("health", __name__)
    health_bp.route("/")(health_endpoint)
    jsonrpc_bp = api.as_blueprint()

    git_get_status = partial(status, path=config.mount_path)
    git_get_status.__doc__ = """Execute \"git status --porcelain=v2 --branch\" on the repository.

Returns:
    dict: A dictionary with several keys:
    'clean': boolean indicating if the repository is clean
    'ahead': integer indicating how many commits the local repo is ahead of the remote
    'behind': integer indicating how many commits the local repo is behind of the remote
    'branch': string with the name of the current branch
    'commit': string with the current commit SHA
    'status': string with the 'raw' result from running git status in the repository
    """
    autosave_create = partial(
        autosave,
        path=config.mount_path,
        git_proxy_health_port=config.git_proxy_health_port,
    )
    renku_run = partial(renku, path=config.mount_path)
    renku_run.__doc__ = """Execute a renku command in the repository.

Additional keyword arguments that are passed will be passed to the renku command.

Args:
    command_name (str): The name of the renku cli command that should be run.
    """

    api.dispatcher.add_method(git_get_status, "git/get_status")
    api.dispatcher.add_method(autosave_create, "autosave/create")
    api.dispatcher.add_method(renku_run, "renku/run")
    app.register_blueprint(jsonrpc_bp, url_prefix=urljoin(config.url_prefix, "jsonrpc"))
    app.register_blueprint(health_bp, url_prefix=urljoin(config.url_prefix, "health"))

    if config.sentry.enabled:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=config.sentry.dsn,
            environment=config.sentry.environment,
            integrations=[FlaskIntegration()],
            traces_sample_rate=config.sentry.sample_rate,
        )
    return app
