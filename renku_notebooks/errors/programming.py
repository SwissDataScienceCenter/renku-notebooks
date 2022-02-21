from .common import GenericError


class ProgrammingError(GenericError):
    """
    *Error codes: from 2000 to 2999*

    The programming errors are bugs or unexpected cases. In the first case, they should lead
    to creating a new GitHub issue; in the latter, it may be necessary to handle the specific
    error to provide the user a precise explanation.
    """

    default_message = "You have found a bug."
    default_status_code = 500
    default_code = 2000


class ConfigurationError(ProgrammingError):
    default_message = (
        "There seems to to be a misconfiguration in Renku, "
        "please contact you administrator."
    )
    default_code = 2001


class FilteringResourcesError(ProgrammingError):
    default_message = (
        "Filtering matched an unexpected "
        "number of resources. Either 1 or 0 resources are expected "
        "to be found."
    )
    default_code = 2002
