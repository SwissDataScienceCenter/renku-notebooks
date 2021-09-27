from jsonrpc import JSONRPCResponseManager, dispatcher
from jsonrpc.exceptions import JSONRPCError
import os
from werkzeug.wrappers import Request, Response

from git_rpc_server import config
from git_rpc_server.methods import git, resources


@Request.application
def application(request):
    """Listen for incoming requests on /jsonrpc"""
    # We currently work on only one repo, the path to this
    # repo is 'hardcoded' through the environment variable.
    os.chdir(os.environ.get("MOUNT_PATH"))
    # Add all methods
    dispatcher.add_method(git.status, "git/status")
    dispatcher.add_method(resources.disk_usage, "resources/diskUsage")
    if config.RPC_SERVER_AUTH_TOKEN == request.headers.get(
        config.RPC_SERVER_AUTH_HEADER_KEY
    ):
        response = JSONRPCResponseManager.handle(request.data, dispatcher)
        return Response(response.json, mimetype="application/json")
    return Response(
        JSONRPCError(-32601, "Authentication is required.").json,
        mimetype="application/json",
    )
