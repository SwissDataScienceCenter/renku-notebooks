from flask import jsonify, Blueprint

from ..auth import authenticated
from .utils import _read_server_options_file
from ... import config


bp = Blueprint("server_options_blueprint", __name__, url_prefix=config.SERVICE_PREFIX,)


@bp.route("server_options")
@authenticated
def server_options(user):
    """Return a set of configurable server options."""
    server_options = _read_server_options_file()

    # TODO: append image-specific options to the options json
    return jsonify(server_options)
