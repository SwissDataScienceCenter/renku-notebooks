from marshmallow import Schema, fields, post_load, post_dump

from .. import config
from .custom_fields import UnionField


class ServersPostRequest(Schema):
    namespace = fields.Str(required=True)
    project = fields.Str(required=True)
    branch = fields.Str(missing="master")
    commit_sha = fields.Str(required=True)
    notebook = fields.Str(missing=None)
    image = fields.Str(missing=None)
    server_options = fields.Dict(
        keys=fields.Str(), missing={}, data_key="serverOptions"
    )


UserPodAnnotations = Schema.from_dict(
    {
        f"{config.RENKU_ANNOTATION_PREFIX}namespace": fields.Str(required=True),
        f"{config.RENKU_ANNOTATION_PREFIX}projectId": fields.Str(required=True),
        f"{config.RENKU_ANNOTATION_PREFIX}projectName": fields.Str(required=True),
        f"{config.RENKU_ANNOTATION_PREFIX}branch": fields.Str(required=True),
        f"{config.RENKU_ANNOTATION_PREFIX}commit-sha": fields.Str(required=True),
        f"{config.RENKU_ANNOTATION_PREFIX}default_image_used": fields.Str(
            required=True
        ),
        f"{config.RENKU_ANNOTATION_PREFIX}repository": fields.Str(required=True),
        f"{config.JUPYTERHUB_ANNOTATION_PREFIX}servername": fields.Str(required=True),
        f"{config.JUPYTERHUB_ANNOTATION_PREFIX}username": fields.Str(required=True),
    }
)


class UserPodResources(Schema):
    cpu = fields.Str()
    memory = fields.Str()


class ServersPostResponse(Schema):
    annotations = fields.Nested(UserPodAnnotations())
    name = fields.Str()
    state = fields.Dict()
    started = fields.DateTime(format="iso")
    status = fields.Dict()
    url = fields.Str()
    resources = fields.Nested(UserPodResources())
    image = fields.Str()


class ServersGetResponse(Schema):
    servers = fields.Dict(
        keys=fields.Str(), values=fields.Nested(ServersPostResponse())
    )


class DefaultResponseSchema(Schema):
    messages = fields.Dict(keys=fields.Str(), values=fields.Str())


class FailedParsing(Schema):
    messages = fields.Dict(
        keys=fields.Str(),
        values=fields.Dict(keys=fields.Str, values=fields.List(fields.Str())),
    )


class ServerOptionsOption(Schema):
    default = UnionField(
        [
            fields.Str(required=True),
            fields.Number(required=True),
            fields.Bool(required=True),
        ]
    )
    displayName = fields.Str(required=True)
    order = fields.Int(required=True)
    type = fields.Str(required=True)
    options = fields.List(UnionField([fields.Str(), fields.Number()]))


class ServerOptions(Schema):
    cpu_request = fields.Nested(ServerOptionsOption())
    defaultUrl = fields.Nested(ServerOptionsOption())
    gpu_request = fields.Nested(ServerOptionsOption())
    lfs_auto_fetch = fields.Nested(ServerOptionsOption())
    mem_request = fields.Nested(ServerOptionsOption())


class ServerLogs(Schema):
    items = fields.List(fields.Str())

    @post_dump
    @post_load
    def remove_item_key(self, data, **kwargs):
        return data.get("items", [])


class AuthState(Schema):
    access_token = fields.Str()
    gitlab_user = fields.Dict(keys=fields.Str())


class User(Schema):
    admin = fields.Bool()
    auth_state = fields.Nested(AuthState(), missing=None)
    created = fields.DateTime(format="iso")
    groups = fields.List(fields.Str())
    kind = fields.Str()
    last_activity = fields.DateTime(format="iso")
    name = fields.Str()
    pending = fields.Str(missing=None)
    server = fields.Str(missing=None)
    servers = fields.Dict(
        keys=fields.Str(), values=fields.Nested(ServersPostResponse()), missing={}
    )
