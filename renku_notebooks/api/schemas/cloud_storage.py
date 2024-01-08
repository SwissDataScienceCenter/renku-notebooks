from configparser import ConfigParser
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from marshmallow import EXCLUDE, Schema, ValidationError, fields, validates_schema

from ...config import config
from ..classes.user import User


class RCloneStorageRequest(Schema):
    class Meta:
        unknown = EXCLUDE

    source_path: Optional[str] = fields.Str()
    target_path: Optional[str] = fields.Str()
    configuration: Optional[Dict[str, Any]] = fields.Dict(
        keys=fields.Str(), values=fields.Raw(), load_default=None, allow_none=True
    )
    storage_id: Optional[str] = fields.Str(load_default=None, allow_none=True)
    readonly: bool = fields.Bool(load_default=True, allow_none=False)
    _mount_folder = None

    @validates_schema
    def validate_storage(self, data, **kwargs):
        if data.get("storage_id") and (data.get("source_path") or data.get("target_path")):
            raise ValidationError(
                "'storage_id' cannot be used together with 'source_path' or 'target_path'"
            )


class RCloneStorage:
    def __init__(
        self,
        source_path: str,
        configuration: Dict[str, Any],
        readonly: bool,
        mount_folder: str,
        name: Optional[str],
    ) -> None:
        config.storage_validator.validate_storage_configuration(configuration, source_path)
        self.configuration = configuration
        self.source_path = source_path
        self.mount_folder = mount_folder
        self.readonly = readonly
        self.name = name

    @classmethod
    def storage_from_schema(cls, data: Dict[str, Any], user: User, project_id: int, work_dir: Path):
        name = None
        if data.get("storage_id"):
            # Load from storage service
            if user.access_token is None:
                raise ValidationError("Storage mounting is only supported for logged-in users.")
            if project_id < 1:
                raise ValidationError("Could not get gitlab project id")
            (
                configuration,
                source_path,
                target_path,
                readonly,
                name,
            ) = config.storage_validator.get_storage_by_id(user, project_id, data["storage_id"])
            configuration = {**configuration, **(configuration or {})}
            readonly = readonly
        else:
            source_path = data["source_path"]
            target_path = data["target_path"]
            configuration = data["configuration"]
            readonly = data.get("readonly", True)
        mount_folder = str(work_dir / target_path)

        return cls(source_path, configuration, readonly, mount_folder, name)

    def get_manifest_patch(
        self, base_name: str, namespace: str, labels={}, annotations={}
    ) -> List[Dict[str, Any]]:
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
                            "kind": "PersistentVolume",
                            "metadata": {
                                "name": base_name,
                                "labels": {"name": base_name},
                            },
                            "spec": {
                                "accessModes": [
                                    "ReadOnlyMany" if self.readonly else "ReadWriteMany"
                                ],
                                "capacity": {"storage": "10Gi"},
                                "storageClassName": "rclone",
                                "csi": {
                                    "driver": "csi-rclone",
                                    "volumeHandle": base_name or base_name,
                                    "volumeAttributes": {
                                        "remote": self.name,
                                        "remotePath": self.source_path,
                                        "configData": self.config_string(self.name or base_name),
                                    },
                                },
                            },
                        },
                    },
                    {
                        "op": "add",
                        "path": f"/{base_name}-pvc",
                        "value": {
                            "apiVersion": "v1",
                            "kind": "PersistentVolumeClaim",
                            "metadata": {
                                "name": base_name,
                                "namespace": namespace,
                            },
                            "spec": {
                                "storageClassName": "rclone",
                                "accessModes": [
                                    "ReadOnlyMany" if self.readonly else "ReadWriteMany"
                                ],
                                "resources": {"requests": {"storage": "10Gi"}},
                            },
                        },
                    },
                    {
                        "op": "add",
                        "path": "/statefulset/spec/template/spec/containers/0/volumeMounts/-",
                        "value": {
                            "mountPath": self.mount_folder,
                            "name": base_name,
                        },
                    },
                    {
                        "op": "add",
                        "path": "/statefulset/spec/template/spec/volumes/-",
                        "value": {
                            "name": base_name,
                            "persistentVolumeClaim": {"claimName": base_name},
                        },
                    },
                ],
            }
        )
        return patches

    def config_string(self, name: str) -> str:
        if not self.configuration:
            raise ValidationError("Missing configuration for cloud storage")
        if (
            self.configuration["type"] == "s3"
            and self.configuration.get("provider", None) == "Switch"
        ):
            # Switch is a fake provider we add for users, we need to replace it since rclone itself
            # doesn't know it
            self.configuration["provider"] = "Other"
        parser = ConfigParser()
        parser.add_section(name)
        for k, v in self.configuration.items():
            parser.set(name, k, v)
        stringio = StringIO()
        parser.write(stringio)
        return stringio.getvalue()


class LaunchNotebookResponseCloudStorage(RCloneStorageRequest):
    class Meta:
        fields = ("remote", "mount_folder", "type")
