from flask import jsonify

from ..auth import authenticated
from .utils import _read_server_options_file
from .blueprints import servers_bp


@servers_bp.route("server_options")
@authenticated
def server_options(user):
    """Return a set of configurable server options."""
    server_options = _read_server_options_file()

    # TODO: append image-specific options to the options json
    return jsonify(server_options)
