from marshmallow import EXCLUDE, Schema, ValidationError, fields, post_load

from ...config import config
from ..classes.cloud_storage.azure_blob import AzureBlobRequest
from ..classes.cloud_storage.s3mount import S3Request


class RCloneStorageRequest(Schema):
    class Meta:
        unknown = EXCLUDE

    source_path = fields.Str()
    target_path = fields.Str()
    configuration = fields.Dict(keys=fields.Str(), values=fields.Raw())

    @post_load
    def create_cloud_storage_object(self, data, **kwargs):
        configuration = data["configuration"]
        path = data["source_path"].lstrip("/")
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
                mount_folder=data["target_path"],
                source_folder=source_path,
                read_only=config.cloud_storage.azure_blob.read_only,
            )
        elif configuration.get("type") == "s3" and config.cloud_storage.s3.enabled:
            cloud_storage = S3Request(
                endpoint=configuration.get("endpoint"),
                bucket=bucket,
                access_key=configuration.get("access_key_id"),
                secret_key=configuration.get("secret_access_key"),
                mount_folder=data["target_path"],
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
                f"Cannot find bucket {data['bucket']} at endpoint {data['endpoint']}. "
                "Please make sure you have provided the correct "
                "credentials, bucket name and endpoint."
            )
        return cloud_storage


class LaunchNotebookResponseCloudStorage(RCloneStorageRequest):
    class Meta:
        fields = ("endpoint", "bucket", "mount_folder")
