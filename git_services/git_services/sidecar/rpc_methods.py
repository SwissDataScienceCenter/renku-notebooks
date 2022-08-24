"""RPC Server methods.

Note that all docstrings of functions below are templated into a <pre></pre> section
in the method map that is automatically published by the server as html.
"""
from git_services.sidecar.commands import base
from git_services.sidecar.config import config_from_env
from git_services.sidecar.errors import json_rpc_errors, JSONRPCGenericError


@json_rpc_errors
def status():
    """Execute \"git status --porcelain=v2 --branch\" on the repository.

    Returns:
        dict: A dictionary with several keys:
        'clean': boolean indicating if the repository is clean (mandatory)
        'ahead': integer indicating how many commits the local repo is ahead of the remote (mandatory)
        'behind': integer indicating how many commits the local repo is behind of the remote (mandatory)
        'branch': string with the name of the current branch (mandatory)
        'commit': string with the current commit SHA (mandatory)
        'status': string with the 'raw' result from running git status in the repository (mandatory)

    Example RPC json response:
    {
        'result': {
            'clean': True,
            'ahead': 0,
            'behind': 0,
            'branch': 'master',
            'commit': '55234e13ede9947718ce765377b86603b2446a1a',
            'status': '# branch.oid 55234e13ede9947718ce765377b86603b2446a1a\n# branch.head master\n# branch.upstream origin/master\n# branch.ab +0 -0\n'
        },
        'id': 0,
        'jsonrpc': '2.0'
    }

    """  # noqa
    config = config_from_env()
    return base.status(path=config.mount_path)


@json_rpc_errors
def autosave():
    """Create an autosave branch with uncommitted work and push it to the remote.

    Returns:
        str, the name of the autosave branch, empty if there was no need to create a branch (mandatory)

    Example RPC json response:
    {
        'result': 'renku/autosave/username/master/55234e1/55234e1',
        'id': 0,
        'jsonrpc': '2.0'
    }
    """  # noqa
    config = config_from_env()
    return base.autosave(path=config.mount_path, git_proxy_health_port=config.git_proxy_health_port)


@json_rpc_errors
def renku(command_name: str, **kwargs):
    """Run a renku command in the session repository.

    Please note that only a limited subset of commands are allowed.

    Args:
        "command_name": str indicating the renku command to run (mandatory)
        Additional keyword arguments are allowed and are passed on to the renku command (optional)

    Returns:
        str, the output from running the command (mandatory)

    Example RPC json response:
    {
        'result': 'Command executed sucessfully',
        'id': 0,
        'jsonrpc': '2.0'
    }
    """
    config = config_from_env()
    return base.renku(path=config.mount_path, command_name=command_name, **kwargs)


@json_rpc_errors
def error():
    """This endpoint will always return an error.

    This is used just to document the format and content of errors from the RPC server. The
    errors respect the JSON-RPC 2.0 specification (https://www.jsonrpc.org/specification).

    Returns:
        dict: A dictionary with several keys:
        code: int, an integer inidcating the status (mandatory)
        messsage: str, error message (mandatory)
        data: cab be a primitive or structured type with additional information (optional)

    Example RPC json response:
    {
        'error': {
            'code': -32603,
            'message': 'Something went wrong',
        },
        'id': 0,
        'jsonrpc': '2.0'
    }
    """
    raise JSONRPCGenericError()
