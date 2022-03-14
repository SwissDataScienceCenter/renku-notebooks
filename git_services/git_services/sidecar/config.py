from dataclasses import dataclass
import dataconf

from git_services.cli.sentry import SentryConfig


@dataclass
class Config:
    sentry: SentryConfig


def config_from_env() -> Config:
    return dataconf.env("GIT_RPC_", Config)
