from dataclasses import dataclass
from marshmallow import Schema, ValidationError, fields, validate
from typing import Dict, Text, Any, Union

from ..api.schemas.custom_fields import ByteSizeField, CpuField, GpuField


class _BaseServerOptionsChoice(Schema):
    order = fields.Int(required=True, validate=lambda x: x >= 1)
    displayName = fields.Str(required=True)
    type = fields.Str(required=True, validate=validate.OneOf(["enum", "boolean"]))


class _CpuServerOptionsChoice(_BaseServerOptionsChoice):
    default = CpuField(required=True)
    options = fields.List(CpuField(required=True))
    value_range = fields.Nested(
        Schema.from_dict(
            {
                "min": CpuField(required=True),
                "max": CpuField(required=True),
                # NOTE: type is unused, left in for backwards compatibility with older Helm charts
                "type": fields.Str(required=False),
            }
        ),
        required=False,
    )
    allow_any_value = fields.Bool(
        required=False, load_default=False, dump_default=False
    )


class _GpuServerOptionsChoice(_BaseServerOptionsChoice):
    default = GpuField(required=True)
    options = fields.List(GpuField(required=True))
    value_range = fields.Nested(
        Schema.from_dict(
            {
                "min": GpuField(required=True),
                "max": GpuField(required=True),
                # NOTE: type is unused, left in for backwards compatibility with older Helm charts
                "type": fields.Str(required=False),
            }
        ),
        required=False,
    )
    allow_any_value = fields.Bool(
        required=False, load_default=False, dump_default=False
    )


class _MemoryServerOptionsChoice(_BaseServerOptionsChoice):
    default = ByteSizeField(required=True)
    options = fields.List(ByteSizeField(required=True))
    value_range = fields.Nested(
        Schema.from_dict(
            {
                "min": ByteSizeField(required=True),
                "max": ByteSizeField(required=True),
                # NOTE: type is unused, left in for backwards compatibility with older Helm charts
                "type": fields.Str(required=False),
            }
        ),
        required=False,
    )
    allow_any_value = fields.Bool(
        required=False, load_default=False, dump_default=False
    )


class _StringServerOptionsChoice(_BaseServerOptionsChoice):
    default = fields.Str(required=True)
    options = fields.List(fields.Str(required=True))


class _BoolServerOptionsChoice(_BaseServerOptionsChoice):
    default = fields.Bool(required=True)


class _ServerOptionsChoices(Schema):
    """Used to deserialize (load) the server options choices from the Helm values file."""

    defaultUrl = fields.Nested(_StringServerOptionsChoice, required=False)
    cpu_request = fields.Nested(_CpuServerOptionsChoice, required=False)
    mem_request = fields.Nested(_MemoryServerOptionsChoice, required=False)
    disk_request = fields.Nested(_MemoryServerOptionsChoice, required=False)
    lfs_auto_fetch = fields.Nested(_BoolServerOptionsChoice, required=False)
    gpu_request = fields.Nested(_GpuServerOptionsChoice, required=False)


class _ServerOptionsDefaults(Schema):
    """Used to deserialize (load) the server options defaults from the Helm values file."""

    defaultUrl = fields.Str(required=True)
    cpu_request = CpuField(required=True)
    mem_request = ByteSizeField(required=True)
    disk_request = ByteSizeField(required=True)
    lfs_auto_fetch = fields.Bool(required=True)
    gpu_request = GpuField(required=True)


class _CloudStorageServerOption(Schema):
    """Used to indicate in the server_options endpoint which types of cloud storage is enabled."""

    s3 = fields.Nested(
        Schema.from_dict({"enabled": fields.Bool(required=True)})(),
        required=True,
    )


class _ServerOptionsEndpointResponse(_ServerOptionsChoices):
    """Used to serialize the server options sent out through the server_options endpoint."""

    cloudstorage = fields.Nested(_CloudStorageServerOption(), required=True)


def get_validator(field_name, server_options_ui, server_options_defaults):
    def _validate(value):
        if field_name in server_options_ui:
            if server_options_ui[field_name].get("allow_any_value", False):
                return True
            elif "value_range" in server_options_ui[field_name]:
                within_range = (
                    value >= server_options_ui[field_name]["value_range"]["min"]
                    and value <= server_options_ui[field_name]["value_range"]["max"]
                )
                if not within_range:
                    raise ValidationError(
                        f"Provided {field_name} value not within allowed range of "
                        f"{server_options_ui[field_name]['value_range']['min']} and "
                        f"{server_options_ui[field_name]['value_range']['max']}."
                    )
            else:
                if value not in server_options_ui[field_name]["options"]:
                    raise ValidationError(
                        f"Provided {field_name} value is not in the allowed options "
                        f"{server_options_ui[field_name]['options']}"
                    )
        else:
            if value != server_options_defaults[field_name]:
                raise ValidationError(
                    f"Provided {field_name} value does not match the allowed value of "
                    f"{server_options_defaults[field_name]}"
                )

    return _validate


@dataclass
class _ServerOptionsConfig:
    defaults_path: Text
    ui_choices_path: Text

    def __post_init__(self):
        with open(self.defaults_path) as f:
            self.defaults: Dict[
                str, Union[Text, bool, int, float]
            ] = _ServerOptionsDefaults().loads(f.read())
        with open(self.ui_choices_path) as f:
            self.ui_choices: Dict[str, Dict[str, Any]] = _ServerOptionsChoices().loads(
                f.read()
            )
        self.post_request_schema = self._get_launch_request_server_options_schema()
        self.get_request_schema = _ServerOptionsEndpointResponse

    def _get_launch_request_server_options_schema(self):
        class LaunchNotebookRequestServerOptions(Schema):
            defaultUrl = fields.Str(
                required=False,
                missing=self.defaults["defaultUrl"],
            )
            cpu_request = CpuField(
                required=False,
                missing=self.defaults["cpu_request"],
                validate=get_validator(
                    "cpu_request",
                    self.ui_choices,
                    self.defaults,
                ),
            )
            mem_request = ByteSizeField(
                required=False,
                missing=self.defaults["mem_request"],
                validate=get_validator(
                    "mem_request",
                    self.ui_choices,
                    self.defaults,
                ),
            )
            disk_request = ByteSizeField(
                required=False,
                missing=self.defaults["disk_request"],
                validate=get_validator(
                    "disk_request",
                    self.ui_choices,
                    self.defaults,
                ),
            )
            lfs_auto_fetch = fields.Bool(
                required=False, missing=self.defaults["lfs_auto_fetch"]
            )
            gpu_request = GpuField(
                required=False,
                missing=self.defaults["gpu_request"],
                validate=get_validator(
                    "gpu_request",
                    self.ui_choices,
                    self.defaults,
                ),
            )

        return LaunchNotebookRequestServerOptions
