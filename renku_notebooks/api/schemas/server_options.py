from marshmallow import (
    Schema,
    fields,
)

from ...config import SERVER_OPTIONS_DEFAULTS, SERVER_OPTIONS_UI
from .custom_fields import (
    CpuField,
    GpuField,
    MemoryField,
)


class ValidationMixin:
    _field_name = "override_me"

    def _validate(self, value):
        parent_validation_results = super()._validate(value)
        if self._field_name in SERVER_OPTIONS_UI:
            if SERVER_OPTIONS_UI[self._field_name].get("allow_any_value", False):
                return True and parent_validation_results
            if "value_range" in SERVER_OPTIONS_UI[self._field_name]:
                return (
                    value >= SERVER_OPTIONS_UI[self._field_name]["value_range"]["min"]
                    and value
                    <= SERVER_OPTIONS_UI[self._field_name]["value_range"]["max"]
                ) and parent_validation_results
            return (
                value in SERVER_OPTIONS_UI[self._field_name]["options"]
            ) and parent_validation_results
        else:
            (
                value == SERVER_OPTIONS_DEFAULTS[self._field_name]
            ) and parent_validation_results


class LaunchNotebookRequestCpuField(CpuField, ValidationMixin):
    _field_name = "cpu_request"


class LaunchNotebookRequestMemoryField(MemoryField, ValidationMixin):
    _field_name = "mem_request"


class LaunchNotebookRequestGpuField(GpuField, ValidationMixin):
    _field_name = "gpu_request"


class LaunchNotebookRequestDiskField(MemoryField, ValidationMixin):
    _field_name = "disk_request"


class LaunchNotebookRequestServerOptions(Schema):
    defaultUrl = fields.Str(required=True)
    cpu_request = LaunchNotebookRequestCpuField(required=False)
    mem_request = LaunchNotebookRequestMemoryField(required=False)
    disk_request = LaunchNotebookRequestDiskField(required=False)
    lfs_auto_fetch = fields.Bool(required=True)
    gpu_request = LaunchNotebookRequestGpuField(required=False)
