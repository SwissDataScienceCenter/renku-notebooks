from git_services.sidecar.app import get_app
from git_services.sidecar.config import config_from_env

_config = config_from_env()
bind = f"{_config.host}:{_config.port}"
app = get_app()
wsgi_app = f"{__name__}:app"
worker_class = "gevent"
