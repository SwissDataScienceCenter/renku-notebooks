"""Schema for cloudstorage config."""

from configparser import ConfigParser
from io import StringIO
from pathlib import Path
from typing import Any, Optional

from marshmallow import EXCLUDE, Schema, ValidationError, fields, validates_schema

from ...config import config
from ..classes.user import User


class RCloneStorageRequest(Schema):
    """Request for RClone based storage."""

    class Meta:
        unknown = EXCLUDE

    source_path: Optional[str] = fields.Str()
    target_path: Optional[str] = fields.Str()
    configuration: Optional[dict[str, Any]] = fields.Dict(
        keys=fields.Str(), values=fields.Raw(), load_default=dict, allow_none=True
    )
    storage_id: Optional[str] = fields.Str(load_default=None, allow_none=True)
    readonly: bool = fields.Bool(load_default=True, allow_none=False)

    @validates_schema
    def validate_storage(self, data, **kwargs):
        """Validate a storage request."""
        if data.get("storage_id") and (data.get("source_path") or data.get("target_path")):
            raise ValidationError("'storage_id' cannot be used together with 'source_path' or 'target_path'")


class RCloneStorage:
    """RClone based storage."""

    def __init__(
        self,
        source_path: str,
        configuration: dict[str, Any],
        readonly: bool,
        mount_folder: str,
        name: Optional[str],
        secrets: dict[str, str],
        user_secret_key: str,
    ) -> None:
        config.storage_validator.validate_storage_configuration(configuration, source_path)
        self.configuration = configuration
        self.source_path = source_path
        self.mount_folder = mount_folder
        self.readonly = readonly
        self.name = name
        self.secrets = secrets
        self.user_secret_key = user_secret_key
        self.base_name: Optional[str] = None

    @classmethod
    def storage_from_schema(cls, data: dict[str, Any], user: User, endpoint: str, work_dir: Path, user_secret_key: str):
        """Create storage object from request."""
        name = None
        if data.get("storage_id"):
            # Load from storage service
            if user.access_token is None:
                raise ValidationError("Storage mounting is only supported for logged-in users.")
            (
                configuration,
                source_path,
                target_path,
                readonly,
                name,
                secrets,
            ) = config.storage_validator.get_storage_by_id(user, endpoint, data["storage_id"])
            configuration = {**configuration, **(data.get("configuration", {}))}
            readonly = readonly
        else:
            source_path = data["source_path"]
            target_path = data["target_path"]
            configuration = data["configuration"]
            readonly = data.get("readonly", True)
            secrets = {}
        mount_folder = str(work_dir / target_path)

        return cls(source_path, configuration, readonly, mount_folder, name, secrets, user_secret_key)

    def get_manifest_patch(self, base_name: str, namespace: str, labels={}, annotations={}) -> list[dict[str, Any]]:
        """Get server manifest patch."""
        self.base_name = base_name
        patches = []
        patches.append(
            {
                "type": "application/json-patch+json",
                "patch": [
                    {
                        "op": "add",
                        "path": f"/{base_name}-pv",
                        "value": {
                            "apiVersion": "v1",
                            "kind": "PersistentVolumeClaim",
                            "metadata": {
                                "name": base_name,
                                "labels": {"name": base_name},
                            },
                            "spec": {
                                "accessModes": ["ReadOnlyMany" if self.readonly else "ReadWriteMany"],
                                "resources": {"requests": {"storage": "10Gi"}},
                                "storageClassName": config.cloud_storage.storage_class,
                            },
                        },
                    },
                    {
                        "op": "add",
                        "path": f"/{base_name}-secret",
                        "value": {
                            "apiVersion": "v1",
                            "kind": "Secret",
                            "metadata": {
                                "name": base_name,
                                "labels": {"name": base_name},
                            },
                            "type": "Opaque",
                            "stringData": {
                                "remote": self.name or base_name,
                                "remotePath": self.source_path,
                                "secretKey": self.user_secret_key,
                                "configData": self.config_string(self.name or base_name),
                            },
                        },
                    },
                    {
                        "op": "add",
                        "path": "/statefulset/spec/template/spec/containers/0/volumeMounts/-",
                        "value": {
                            "mountPath": self.mount_folder,
                            "name": base_name,
                            "readOnly": self.readonly,
                        },
                    },
                    {
                        "op": "add",
                        "path": "/statefulset/spec/template/spec/volumes/-",
                        "value": {
                            "name": base_name,
                            "persistentVolumeClaim": {
                                "claimName": base_name,
                                "readOnly": self.readonly,
                            },
                        },
                    },
                ],
            }
        )
        return patches

    def config_string(self, name: str) -> str:
        """Convert the configuration object to string representation.

        Needed to create RClone compatible INI files.
        """
        if not self.configuration:
            raise ValidationError("Missing configuration for cloud storage")
        real_config = dict(self.configuration)
        if real_config["type"] == "s3" and real_config.get("provider") == "Switch":
            # Switch is a fake provider we add for users, we need to replace it since rclone itself
            # doesn't know it
            real_config["provider"] = "Other"
        elif real_config["type"] == "openbis":
            real_config["type"] = "sftp"
            real_config["port"] = "2222"
            real_config["user"] = "?"
            real_config["pass"] = real_config.pop("session_token")
        parser = ConfigParser()
        parser.add_section(name)

        def _stringify(value):
            if isinstance(value, bool):
                return "true" if value else "false"
            return str(value)

        for k, v in real_config.items():
            parser.set(name, k, _stringify(v))
        stringio = StringIO()
        parser.write(stringio)
        return stringio.getvalue()


class LaunchNotebookResponseCloudStorage(RCloneStorageRequest):
    """Notebook launch response with cloud storage attached."""

    class Meta:
        fields = ("remote", "mount_folder", "type")
