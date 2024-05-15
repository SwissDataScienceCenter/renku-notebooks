"""RPC Server methods.

Note that all docstrings of functions below are templated into a <pre></pre> section
in the method map that is automatically published by the server as html.
"""

from git_services.sidecar.commands import base
from git_services.sidecar.config import config_from_env
from git_services.sidecar.errors import JSONRPCGenericError, json_rpc_errors


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


@json_rpc_errors
def discard_unsaved_changes():
    """Completely discards changes that are not pushed to the repository's remote.

    This is used to prevent the creation of persistent sessions if the user decides to shut down
    their sessions but has unsaved data that they simnply wish to discard.
    This is the equivalent of answering "No" when asked by a word editor "Do you want to save
    the unsaved changes?" before closing an opened document.

    No arguments are allowed or required. Nothing is returned.

    Example RPC json response:
    {
        'result': null,
        'id': 0,
        'jsonrpc': '2.0'
    }
    """
    # TODO: How should we deal with case!?
    config = config_from_env()
    base.discard_unsaved_changes(path=config.mount_path)


@json_rpc_errors
def pull():
    """Pull the latest changes from the remote.

    Only fast-forwarding is allowed. If a merge-commit is required the command will fail.

    Example RPC json response:
    {
        'result': null,
        'id': 0,
        'jsonrpc': '2.0'
    }
    """
    config = config_from_env()
    base.pull(path=config.mount_path, fast_forward_only=True)
