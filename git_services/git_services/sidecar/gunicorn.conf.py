from git_services.sidecar.config import config_from_env

_config = config_from_env()
bind = f"{_config.host}:{_config.port}"
wsgi_app = "git_services.sidecar.app:app"
worker_class = "gevent"
