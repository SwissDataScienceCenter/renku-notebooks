from dataclasses import dataclass
from typing import Optional

from .common import GenericError


@dataclass
class IntermittentError(GenericError):
    """
    *Error codes: from 3000 to 3999*

    This category includes errors that may temporarily affect the user, but they don't depend
    on a wrong input or can be classified as a bug. Repeating the same action after some
    time should be enough to solve the problem. If this is not the case then the
    system administrator or cloud provider can resolve these errors.
    An example could be a temporarily unavailable backend service (E.G. the GitLab instance)
    or a transient network problem.
    """

    message: str = (
        "We seem to be experiencing some technical difficulties, please try again later."
    )
    code: int = 3000
    status_code: int = 500
    detail: Optional[str] = "If this problem persists please contact your administrator."


@dataclass
class DeleteServerError(IntermittentError):
    message: str = (
        "The server cannot be deleted, most likely due to problems "
        "with the underlying infrastructure."
    )
    code: int = 3001


@dataclass
class CannotStartServerError(IntermittentError):
    message: str = (
        "Cannot start the server, most likely due to problems "
        "with the underlying infrastructure."
    )
    code: int = 3002
