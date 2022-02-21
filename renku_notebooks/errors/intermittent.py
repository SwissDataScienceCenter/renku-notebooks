from .common import GenericError


class IntermittentError(GenericError):
    """
    *Error codes: from 3000 to 3999*

    This category includes errors that may temporarily affect the user, but they don't depend
    on a wrong input and can be classified as a bug. Repeating the same action after some
    time should be enough to solve the problem.
    An example could be a temporarily unavailable backend service (E.G. the GitLab instance)
    or a transient network problem.
    """

    default_message = "We seem to be having some issues, please try again later."
    default_status_code = 500
    default_code = 3000


class DeleteServerError(IntermittentError):
    default_message = "The server cannot be deleted."
    default_code = 3001


class CannotStartServerError(IntermittentError):
    default_message = "Cannot start the server."
    default_detail = (
        "This is most likely due to problems with Kubernetes "
        "or underlying infrastructure."
    )
    default_code = 3002
