from marshmallow import fields, Schema, ValidationError, validates_schema

from .custom_fields import LowercaseString
from .server_options import LaunchNotebookRequestServerOptions
from .cloud_storage import LaunchNotebookRequestS3mount
from ... import config


class LaunchNotebookRequestWithoutS3(Schema):
    """Used to validate the requesting for launching a jupyter server"""

    # namespaces in gitlab are NOT case sensitive
    namespace = LowercaseString(required=True)
    # project names in gitlab are NOT case sensitive
    project = LowercaseString(required=True)
    # branch names in gitlab are case sensitive
    branch = fields.Str(load_default="master")
    commit_sha = fields.Str(required=True)
    notebook = fields.Str(load_default=None)
    image = fields.Str(load_default=None)
    server_options = fields.Nested(
        LaunchNotebookRequestServerOptions(),
        load_default=config.SERVER_OPTIONS_DEFAULTS,
        data_key="serverOptions",
        required=False,
    )


class LaunchNotebookRequestWithS3(LaunchNotebookRequestWithoutS3):
    """Used to validate the requesting for launching a jupyter server"""

    cloudstorage = fields.List(
        fields.Nested(LaunchNotebookRequestS3mount()),
        required=False,
        load_default=[],
    )

    @validates_schema
    def validate_unique_bucket_names(self, data, **kwargs):
        errors = {}
        bucket_names = [i.bucket for i in data["cloudstorage"]]
        bucket_names_unique = set(bucket_names)
        if len(bucket_names_unique) < len(bucket_names):
            errors["cloudstorage"] = [
                "Found duplicate storage bucket names. "
                "All provided bucket names have to be unique"
            ]
        if errors:
            raise ValidationError(errors)


LaunchNotebookRequest = (
    LaunchNotebookRequestWithS3
    if config.S3_MOUNTS_ENABLED
    else LaunchNotebookRequestWithoutS3
)