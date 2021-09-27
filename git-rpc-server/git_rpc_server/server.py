from jsonrpc import JSONRPCResponseManager, dispatcher
from jsonrpc.exceptions import JSONRPCError
from werkzeug.wrappers import Request, Response

from git_rpc_server import config


@Request.application
def application(request):
    """Setup the json-rpc server."""
    if "token {}".format(config.RPC_SERVER_AUTH_TOKEN) == request.headers.get(
        config.RPC_SERVER_AUTH_HEADER_KEY
    ):
        response = JSONRPCResponseManager.handle(request.data, dispatcher)
        return Response(response.json, mimetype="application/json")
    return Response(
        JSONRPCError(
            -32601,
            "Authorization is required, pass the token in the "
            "`Authorization` header as `token secret_token_value`.",
        ).json,
        mimetype="application/json",
    )
