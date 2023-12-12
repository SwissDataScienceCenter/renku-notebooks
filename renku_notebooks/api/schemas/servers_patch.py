from enum import Enum

from marshmallow import Schema, fields, validate


class PatchServerStatusEnum(Enum):
    """Possible values when patching a server."""

    Running = "running"
    Hibernated = "hibernated"

    @classmethod
    def list(cls):
        return [e.value for e in cls]


class PatchServerRequest(Schema):
    """Simple Enum for server status."""

    state = fields.String(required=False, validate=validate.OneOf(PatchServerStatusEnum.list()))
    resource_class_id = fields.Int(required=False, validate=lambda x: x > 0)
