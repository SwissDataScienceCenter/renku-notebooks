import sys
import traceback


class GitCloneGenericError(Exception):
    """A generic error class that is the parent class of all API errors raised
    by the git clone module."""

    default_exit_code = 200

    def __init__(
        self,
        exit_code=default_exit_code,
    ):
        self.exit_code = exit_code


class GitServerUnavailableError(GitCloneGenericError):
    default_exit_code = 201


class UnexpectedAutosaveFormatError(GitCloneGenericError):
    default_exit_code = 202


class NoDiskSpaceError(GitCloneGenericError):
    default_exit_code = 203


class GitCommandBaseError(GitCloneGenericError):
    default_exit_code = 204


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, GitCloneGenericError):
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        sys.exit(exc_value.exit_code)
    sys.__excepthook__(exc_type, exc_value, exc_traceback)
