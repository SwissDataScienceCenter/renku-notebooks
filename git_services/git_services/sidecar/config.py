from dataclasses import dataclass
from pathlib import Path
from typing import Any, Text, TypeVar, Union

import dataconf

from git_services.cli.sentry import SentryConfig


def _parse_value_as_int(val: Any) -> int:
    # NOTE: That int() does not understand scientific notation
    # even stuff that is "technically" an integer like 3e10, but float does understand it
    return int(float(val))


PathType = TypeVar("PathType", bound=Path)


@dataclass
class Config:
    sentry: SentryConfig
    port: Union[Text, int] = 4000
    host: Text = "0.0.0.0"
    url_prefix: Text = "/"
    mount_path: Union[Text, PathType] = "."
    git_proxy_health_port: Union[Text, int] = 8081

    def __post_init__(self):
        self.port = _parse_value_as_int(self.port)
        self.git_proxy_health_port = _parse_value_as_int(self.git_proxy_health_port)
        if isinstance(self.mount_path, str):
            self.mount_path = Path(self.mount_path)


def config_from_env() -> Config:
    return dataconf.env("GIT_RPC_", Config)
