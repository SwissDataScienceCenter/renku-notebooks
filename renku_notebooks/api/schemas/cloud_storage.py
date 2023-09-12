from marshmallow import EXCLUDE, Schema, ValidationError, fields, post_load

from ...config import config
from ..classes.cloud_storage.azure_blob import AzureBlobRequest
from ..classes.cloud_storage.s3mount import S3Request
from typing import Optional, Any, Dict


class RCloneStorageRequest(Schema):
    class Meta:
        unknown = EXCLUDE

    source_path: Optional[str] = fields.Str()
    target_path: Optional[str] = fields.Str()
    configuration: Optional[Dict[str, Any]] = fields.Dict(
        keys=fields.Str(), values=fields.Raw(), load_default=None, allow_none=True
    )
    storage_id: Optional[str] = fields.Str(load_default=None, allow_none=True)

    @post_load
    def create_cloud_storage_object(self, data, **kwargs):
        if data.get("storage_id") and (
            data.get("source_path") or data.get("target_path")
        ):
            raise ValidationError(
                "'storage_id' cannot be used together with 'source_path' or 'target_path'"
            )
        if data.get("storage_id"):
            # Load from storage service
            (
                configuration,
                source_path,
                target_path,
            ) = config.storage_validator.get_storage_by_id(data["storage_id"])
            configuration = {**configuration, **(data.get("configuration") or {})}
        else:
            source_path = data["source_path"]
            target_path = data["target_path"]
            configuration = data["configuration"]

        config.storage_validator.validate_storage_configuration(configuration)

        path = source_path.lstrip("/")
        if "/" in path:
            bucket, source_path = path.split("/", 1)
        else:
            bucket, source_path = path, ""

        if (
            configuration.get("type") == "azureblob"
            and configuration.get("access_key_id") is None
            and configuration.get("secret_access_key") is not None
            and config.cloud_storage.azure_blob.enabled
        ):
            cloud_storage = AzureBlobRequest(
                endpoint=configuration["endpoint"],
                container=bucket,
                credential=configuration["secret_access_key"],
                mount_folder=target_path,
                source_folder=source_path,
                read_only=config.cloud_storage.azure_blob.read_only,
            )
        elif configuration.get("type") == "s3" and config.cloud_storage.s3.enabled:
            cloud_storage = S3Request(
                endpoint=configuration.get("endpoint"),
                region=configuration.get("region"),
                bucket=bucket,
                access_key=configuration.get("access_key_id"),
                secret_key=configuration.get("secret_access_key"),
                mount_folder=target_path,
                source_folder=source_path,
                read_only=config.cloud_storage.s3.read_only,
            )
        else:
            raise ValidationError(
                "Cannot accept the provided cloud storage parameters because "
                "the requested storage type has not been properly setup or enabled."
            )

        if not cloud_storage.exists:
            raise ValidationError(
                f"Cannot find bucket {bucket} at endpoint {cloud_storage.endpoint}. "
                "Please make sure you have provided the correct "
                "credentials, bucket name and endpoint."
            )
        return cloud_storage


class LaunchNotebookResponseCloudStorage(RCloneStorageRequest):
    class Meta:
        fields = ("endpoint", "bucket", "mount_folder")
