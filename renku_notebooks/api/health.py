from flask import Blueprint, Response, current_app

bp = Blueprint("health_blueprint", __name__)


@bp.route("/health")
def health():
    """Just a health check path."""
    return Response(
        "service running under {}".format(current_app.config["all"].service_prefix)
    )
