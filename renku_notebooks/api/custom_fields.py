from typing import List, Mapping, Any
from marshmallow import fields
from marshmallow.exceptions import ValidationError
import re

from .. import config


class UnionField(fields.Field):
    """
    Field that deserializes multi-type input data to app-level objects.
    Adapted from https://stackoverflow.com/a/64034540
    """

    def __init__(self, val_types: List[fields.Field]):
        self.valid_types = val_types
        super().__init__()

    def _deserialize(
        self, value: Any, attr: str = None, data: Mapping[str, Any] = None, **kwargs
    ):
        """
        _deserialize defines a custom Marshmallow Schema Field that takes in mutli-type
        input data to app-level objects.

        Parameters
        ----------
        value : {Any}
            The value to be deserialized.

        Keyword Parameters
        ----------
        attr : {str} [Optional]
            The attribute/key in data to be deserialized. (default: {None})
        data : {Optional[Mapping[str, Any]]}
            The raw input data passed to the Schema.load. (default: {None})

        Raises
        ----------
        ValidationError : Exception
            Raised when the validation fails on a field or schema.
        """
        errors = []
        # iterate through the types being passed into UnionField via val_types
        for field in self.valid_types:
            try:
                # inherit deserialize method from Fields class
                return field.deserialize(value, attr, data, **kwargs)
            # if error, add error message to error list
            except ValidationError as error:
                errors.append(error.messages)

        raise ValidationError(errors)


serverOptionCpuValue = fields.Number(
    validate=lambda x: x > 0.0 and (x % 1 >= 0.001 or x % 1 == 0.0), required=True
)
serverOptionDiskValue = fields.String(
    validate=lambda x: re.match(r"^(?:[1-9][0-9]*|[0-9]\.[0-9]*)[EPTGMK][i]{0,1}$", x)
    is not None,
    required=False,
    missing=config.SERVER_OPTIONS_DEFAULTS.get("disk_request", "1G"),
)
serverOptionMemoryValue = fields.String(
    validate=lambda x: re.match(r"^(?:[1-9][0-9]*|[0-9]\.[0-9]*)[EPTGMK][i]{0,1}$", x)
    is not None,
    required=True,
)
serverOptionUrlValue = fields.Str(required=True)
