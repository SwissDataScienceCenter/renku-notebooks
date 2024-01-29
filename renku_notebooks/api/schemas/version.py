from marshmallow import Schema, fields


class NotebooksServiceInfo(Schema):
    """Various notebooks service info."""

    anonymous_sessions_enabled = fields.Boolean(required=True)
    cloudstorage_enabled = fields.Boolean(required=True)
    cloudstorage_class = fields.String(required=True)
    ssh_enabled = fields.Boolean(required=True)


class NotebooksServiceVersions(Schema):
    """Notebooks service version and info."""

    data = fields.Nested(NotebooksServiceInfo, required=True)
    version = fields.String(required=True)


class VersionResponse(Schema):
    """The response for /version endpoint."""

    name = fields.String(required=True)
    versions = fields.List(fields.Nested(NotebooksServiceVersions), required=True)
