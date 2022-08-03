import os
from urllib.parse import urljoin

from flask import Flask
from jsonrpc.backend.flask import api, Blueprint

from git_services.sidecar.rpc_server import autosave, status
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
    api.dispatcher.add_method(status, "git/get_status")
    api.dispatcher.add_method(autosave, "autosave/create")
    app.register_blueprint(jsonrpc_bp, url_prefix=urljoin(config.url_prefix, "jsonrpc"))
    app.register_blueprint(health_bp, url_prefix=urljoin(config.url_prefix, "health"))

    if config.sentry.enabled:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=config.sentry.dsn,
            environment=config.sentry.env,
            integrations=[FlaskIntegration()],
            traces_sample_rate=config.sentry.sample_rate,
        )
    return app


app = get_app()
