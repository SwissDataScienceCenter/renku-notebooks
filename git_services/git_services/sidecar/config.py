from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Text, TypeVar, Union

import dataconf

from git_services.cli.sentry import SentryConfig


def _parse_value_as_numeric(val: Any, parse_to: Callable) -> Union[float, int]:
    output = parse_to(val)
    if type(output) is not float and type(output) is not int:
        raise ValueError(
            f"parse_to should convert to float or int, it returned type {type(output)}"
        )
    return output


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
        self.port = _parse_value_as_numeric(self.port, int)
        self.git_proxy_health_port = _parse_value_as_numeric(self.git_proxy_health_port, int)
        if isinstance(self.mount_path, str):
            self.mount_path = Path(self.mount_path)


def config_from_env() -> Config:
    return dataconf.env("GIT_RPC_", Config)
