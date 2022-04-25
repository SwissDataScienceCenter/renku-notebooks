from dataclasses import dataclass
import dataconf
from typing import Optional

from git_services.cli.sentry import SentryConfig


@dataclass
class AuthConfig:
    token: str
    header_key: Optional[str] = "Authorization"


@dataclass
class Config:
    sentry: SentryConfig
    auth: AuthConfig


def config_from_env() -> Config:
    return dataconf.env("GIT_RPC_", Config)
