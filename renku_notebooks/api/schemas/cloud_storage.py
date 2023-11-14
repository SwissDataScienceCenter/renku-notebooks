from configparser import ConfigParser
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from marshmallow import (EXCLUDE, Schema, ValidationError, fields,
                         validates_schema)

from renku_notebooks.errors.programming import ProgrammingError

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

    def init_config(self, data: Dict[str, Any], user: User, project_id: str, work_dir: Path):
        if self.storage_id:
            # Load from storage service
            if user.access_token is None:
                raise ValidationError("Storage mounting is only supported for logged-in users.")
            if project_id < 1:
                raise ValidationError("Could not get gitlab project id")
            (
                configuration,
                self.source_path,
                self.target_path,
                readonly,
            ) = config.storage_validator.get_storage_by_id(user, project_id, self.storage_id)
            self.configuration = {**configuration, **(self.configuration or {})}
            self.readonly = self.readonly
        else:
            self.source_path = data["source_path"]
            self.target_path = data["target_path"]
            self.configuration = data["configuration"]
            self.readonly = self.readonly
        config.storage_validator.validate_storage_configuration(self.configuration)
        self._mount_folder = work_dir / self.target_path

    @property
    def mount_folder(self):
        if not self._mount_folder:
            raise ProgrammingError("mount_folder not set. Ensure init_config was called first.")
        return self._mount_folder

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
                        "path": f"/{base_name}",
                        "value": {
                            "apiVersion": "v1",
                            "kind": "PersistentVolume",
                            "metadata": {
                                "name": base_name,
                                "labels": {"name": base_name},
                                "spec": {
                                    "accessModes": [
                                        "ReadOnlyMany" if self.readonly else "ReadWriteMany"
                                    ],
                                    "capacity": {"storage": "10Gi"},
                                    "storageClassName": "rclone",
                                    "csi": {
                                        "driver": "csi-rclone",
                                        "volumeHandle": base_name,
                                        "volumeAttributes": {
                                            "remote": base_name,
                                            "remotePath": self.source_path,
                                            "configData": self.config_string(base_name),
                                        },
                                    },
                                },
                            },
                        },
                    },
                    {
                        "op": "add",
                        "path": f"/{base_name}",
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
        parser = ConfigParser()
        parser.add_section(name)
        for k, v in self.configuration.items():
            parser.set(name, k, v)
        stringio = StringIO()
        parser.write(stringio)
        return stringio.getvalue()


class LaunchNotebookResponseCloudStorage(RCloneStorageRequest):
    class Meta:
        fields = ("endpoint", "bucket", "mount_folder")
