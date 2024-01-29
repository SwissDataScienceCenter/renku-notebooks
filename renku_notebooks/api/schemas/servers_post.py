from marshmallow import Schema, fields, pre_load

from ...config import config
from .cloud_storage import RCloneStorageRequest
from .custom_fields import LowercaseString
from .server_options import LaunchNotebookRequestServerOptions


class LaunchNotebookRequestWithoutStorage(Schema):
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
    # the server options field is honored only if provided
    # it will be matched against the closest resource class
    server_options = fields.Nested(
        LaunchNotebookRequestServerOptions(),
        required=False,
    )
    resource_class_id = fields.Int(required=False, load_default=None)
    # storage is in gigabytes
    storage = fields.Int(
        required=False,
        load_default=1,
    )
    lfs_auto_fetch = fields.Bool(
        required=False, load_default=config.server_options.defaults["lfs_auto_fetch"]
    )
    default_url = fields.Str(
        required=False,
        load_default=config.server_options.defaults["default_url"],
    )
    environment_variables = fields.Dict(keys=fields.Str(), values=fields.Str(), load_default=dict())

    @pre_load
    def _pre_load(self, data, **kwargs):
        """Compatibility with old clients"""
        if "serverOptions" in data:
            data["server_options"] = data["serverOptions"]
            del data["serverOptions"]
        return data


class LaunchNotebookRequestWithStorage(LaunchNotebookRequestWithoutStorage):
    """Used to validate the requesting for launching a jupyter server"""

    cloudstorage = fields.List(
        fields.Nested(RCloneStorageRequest()),
        required=False,
        load_default=[],
    )


LaunchNotebookRequest = (
    LaunchNotebookRequestWithStorage
    if config.cloud_storage.enabled
    else LaunchNotebookRequestWithoutStorage
)
