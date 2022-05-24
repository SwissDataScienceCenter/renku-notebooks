from dataclasses import dataclass
import dataconf

from git_services.cli.sentry import SentryConfig


@dataclass
class Config:
    sentry: SentryConfig
    port: int = 4000
    host: str = "0.0.0.0"
    url_prefix: str = "/"


def config_from_env() -> Config:
    return dataconf.env("GIT_RPC_", Config)
