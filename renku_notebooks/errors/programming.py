from dataclasses import dataclass
from typing import Optional

from .common import GenericError


@dataclass
class ProgrammingError(GenericError):
    """
    *Error codes: from 2000 to 2999*

    The programming errors are bugs or unexpected cases. In the first case, they should lead
    to creating a new GitHub issue; in the latter, it may be necessary to handle the specific
    error to provide the user a precise explanation.
    """

    message: str = "You have found a bug"
    code: int = 2000
    status_code: int = 500
    detail: Optional[str] = "Please report this to the Renku maintainers."


@dataclass
class ConfigurationError(ProgrammingError):
    message: str = "There seems to to be a misconfiguration in Renku."
    code: int = 2001
    detail: Optional[str] = "Please contact your administrator."


@dataclass
class FilteringResourcesError(ProgrammingError):
    message: str = (
        "Filtering matched an unexpected "
        "number of resources. Either 1 or 0 resources are expected "
        "to be found."
    )
    code: int = 2002
