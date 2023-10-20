# NOTE: We have to patch subprocess with gevent here otherwise when GitPython (or other libraries)
# try to use subprocess.Popen here they will be blocked by gevent. Also this has to be done at the
# top of the file before any other library is imported. Moving this statement a few lines down
# causes GitPython (called from within the Renku CLI) to not work.
from gevent.monkey import patch_all

patch_all()

from git_services.sidecar.app import get_app  # noqa: E402
from git_services.sidecar.config import config_from_env  # noqa: E402

_config = config_from_env()
bind = f"{_config.host}:{_config.port}"
app = get_app()
wsgi_app = f"{__name__}:app"
worker_class = "gevent"
