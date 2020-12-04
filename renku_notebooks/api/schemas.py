from marshmallow import Schema, fields


class ServersPostRequest(Schema):
    namespace = fields.Str(required=True)
    project = fields.Str(required=True)
    branch = fields.Str(missing="master")
    commit_sha = fields.Str(required=True)
    notebook = fields.Str(missing=None)
    image = fields.Str(missing=None)
    server_options = fields.Dict(
        keys=fields.Str(), values=fields.Str(), missing={}, data_key="serverOptions"
    )


class ServersPostResponse(Schema):
    annotations = fields.Dict(keys=fields.Str(), values=fields.Str())
    name = fields.Str()
    state = fields.Dict()
    started = fields.DateTime(format="iso")
    status = fields.Dict()
    url = fields.Str()
    resources = fields.Dict(keys=fields.Str(), values=fields.Str())
    image = fields.Str()


class DefaultResponseSchema(Schema):
    messages = fields.Dict(keys=fields.Str(), values=fields.Str())


class FailedParsing(Schema):
    messages = fields.Dict(
        keys=fields.Str(),
        values=fields.Dict(keys=fields.Str, values=fields.List(fields.Str())),
    )
