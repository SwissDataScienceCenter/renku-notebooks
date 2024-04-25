from dataclasses import dataclass
from pathlib import Path
from typing import List

from marshmallow import Schema, fields, ValidationError


class PathField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return ""
        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):
        path = Path(value)
        if not path.is_absolute():
            raise ValidationError("Path is not aboslute")
        return str(path)


class UserSecrets(Schema):
    # List of ids of the user's secrets
    user_secret_ids = fields.List(fields.Str, required=True)
    # Mount path in the main container
    mount_path = PathField(required=True)


@dataclass
class K8sUserSecrets:
    """Class containing the information for the Kubernetes secret that will
    provide the user secrets
    """

    name: str  # Name of the k8s secret containing the user secrets
    user_secret_ids: List[str]  # List of user secret ids
    mount_path: str  # Path in the container where to mount the k8s secret
