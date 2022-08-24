from typing import Any, Callable, Text, Union

from dataclasses import dataclass
import dataconf

from git_services.cli.sentry import SentryConfig


def _parse_value_as_numeric(val: Any, parse_to: Callable) -> Union[float, int]:
    output = parse_to(val)
    if type(output) is not float and type(output) is not int:
        raise ValueError(
            f"parse_to should convert to float or int, it returned type {type(output)}"
        )
    return output


@dataclass
class Config:
    sentry: SentryConfig
    port: Union[Text, int] = 4000
    host: Text = "0.0.0.0"
    url_prefix: Text = "/"

    def __post_init__(self):
        self.port = _parse_value_as_numeric(self.port, int)


def config_from_env() -> Config:
    return dataconf.env("GIT_RPC_", Config)
