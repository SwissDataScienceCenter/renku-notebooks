import shutil
import sys
import traceback

from git_services.init.config import config_from_env


class GitCloneGenericError(Exception):
    """A generic error class that is the parent class of all API errors raised
    by the git clone module."""

    exit_code = 200


class GitServerUnavailableError(GitCloneGenericError):
    exit_code = 201


class NoDiskSpaceError(GitCloneGenericError):
    exit_code = 203


class BranchDoesNotExistError(GitCloneGenericError):
    exit_code = 204


class GitSubmoduleError(GitCloneGenericError):
    exit_code = 205


class CloudStorageOverwritesExistingFilesError(GitCloneGenericError):
    exit_code = 206


def handle_exception(exc_type, exc_value, exc_traceback):
    # NOTE: To prevent restarts of a failing init container from producing ambiguous errors
    # cleanup the repo after a failure so that a restart of the container produces the same error.
    config = config_from_env()
    shutil.rmtree(config.mount_path, ignore_errors=True)
    if issubclass(exc_type, GitCloneGenericError):
        # INFO: The process failed in a specific way that should be distinguished to the user.
        # The user can take action to correct the failure.
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        sys.exit(exc_value.exit_code)
    else:
        # INFO: A git command failed in a way that does not need to be distinguished to the user.
        # Indicates that something failed in the Git commands but knowing how or what is not
        # useful to the end user of the session and the user cannot correct this.
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        sys.exit(200)
