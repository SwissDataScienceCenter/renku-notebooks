from abc import ABC, abstractmethod


class _GenericErrorBase(ABC):
    """Other than Werkzeug and Marshmallow validation errors,
    the notebook service expects all other errors raised should
    follow this abstract class."""

    @property
    @abstractmethod
    def status_code(self) -> int:
        pass

    @property
    @abstractmethod
    def message(self) -> str:
        pass

    @property
    @abstractmethod
    def code(self) -> int:
        pass

    @property
    @abstractmethod
    def detail(self) -> str:
        pass


class GenericError(_GenericErrorBase, Exception):
    """A generic error class that is the parent class of all API errors raised
    by the notebook service code."""

    default_message = "Something went wrong."
    default_status_code = 500
    default_code = 2000
    default_detail = None

    def __init__(
        self,
        message=default_message,
        status_code=default_status_code,
        code=default_code,
        detail=default_detail,
    ):
        self._message = message
        self._status_code = status_code
        self._code = code
        self._detail = detail

    @property
    def message(self):
        return self._message

    @property
    def status_code(self):
        return self._status_code

    @property
    def code(self):
        return self._code

    @property
    def detail(self):
        return self._detail
