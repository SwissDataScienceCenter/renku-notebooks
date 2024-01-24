from typing import Any, Dict

import pytest

from renku_notebooks.api.schemas.server_options import (
    LaunchNotebookRequestServerOptions,
    ServerOptions,
)


@pytest.mark.parametrize(
    "test_input,expected_value",
    [
        ({}, ServerOptions(0, 0, 0)),
        ({"cpu_request": 2}, ServerOptions(2, 0, 0)),
        ({"mem_request": "2G"}, ServerOptions(0, 2000000000, 0)),
        (
            {"mem_request": "2G", "lfs_auto_fetch": True},
            ServerOptions(0, 2000000000, 0, lfs_auto_fetch=True),
        ),
        (
            {"disk_request": 1000000000, "lfs_auto_fetch": True, "default_url": "/test"},
            ServerOptions(0, 0, 0, 1000000000, lfs_auto_fetch=True, default_url="/test"),
        ),
    ],
)
def test_request_server_options_conversion(
    test_input: Dict[str, Any], expected_value: ServerOptions
):
    req_server_options = LaunchNotebookRequestServerOptions().load(test_input)
    assert req_server_options == expected_value


@pytest.mark.parametrize(
    "test_input,expected_value",
    [
        (
            {"cpu": 1.0, "memory": 3, "default_storage": 10, "gpu": 0},
            ServerOptions(1.0, 3000000000, 0, 10000000000),
        ),
    ],
)
def test_resource_class_conversion(test_input, expected_value):
    assert ServerOptions.from_resource_class(test_input) == expected_value
