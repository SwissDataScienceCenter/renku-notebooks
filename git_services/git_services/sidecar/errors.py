from dataclasses import dataclass
import functools
import logging

from jsonrpc.exceptions import JSONRPCDispatchException
from renku.core.errors import RenkuException

from git_services.cli import GitCommandError


@dataclass
class SidecarGenericError(Exception):
    """Base class for all sidecar error."""
    message: str = "Something went wrong"


@dataclass
class SidecarUserError(SidecarGenericError):
    """An error that can be corrected by the user."""
    message: str


@dataclass
class SidecarProgrammingError(SidecarGenericError):
    """An error that can not be corrected by the user, usually a bug."""
    pass


class JSONRPCGenericError(JSONRPCDispatchException):
    """Base class for all JSON RPC errors."""
    def __init__(self, code=-32603, message="Something went wrong", data=None, *args, **kwargs):
        super().__init__(code, message, data, *args, **kwargs)


class JSONRPCProgrammingError(JSONRPCDispatchException):
    """An error that cannot be corrected by the user the RPC server."""
    def __init__(self, code=-32000, message="Something went wrong", data=None, *args, **kwargs):
        super().__init__(code, message, data, *args, **kwargs)


class JSONRPCUserError(JSONRPCDispatchException):
    """An error that can be corrected by the user the RPC server.

    Usually involves sending invalid parameters or requesting resources that do not exist.
    """
    def __init__(self, code=-32001, message=None, data=None, *args, **kwargs):
        super().__init__(code, message, data, *args, **kwargs)


def json_rpc_errors(func):
    """Convert errors to predictable JSON-RPC format."""
    @functools.wraps(func)
    def _json_rpc_errors(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except JSONRPCDispatchException:
            raise
        except SidecarGenericError as e:
            if isinstance(e, SidecarUserError):
                raise JSONRPCUserError(message=e.message)
            else:
                raise JSONRPCProgrammingError(message=e.message)
        except RenkuException as e:
            raise JSONRPCProgrammingError(
                message=getattr(
                    e,
                    "message",
                    f"Something went wrong running a Renku command, "
                    f"this resulted from Renku error {type(e)}",
                )
            )
        except GitCommandError as e:
            raise JSONRPCProgrammingError(
                message=f"Running a git command failed with the error: {e.stderr}",
            )
        except Exception as e:
            logging.exception(e)
            raise JSONRPCGenericError(
                message=getattr(e, "message", f"Failed with an unexpected error of type {type(e)}")
            )

    return _json_rpc_errors
