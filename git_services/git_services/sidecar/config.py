from dataclasses import dataclass
from typing import Optional
import dataconf


@dataclass
class Sentry:
    enabled: Optional[bool] = False
    dsn: Optional[str] = ""
    environment: Optional[str] = ""
    sample_rate: Optional[float] = 0.0


@dataclass
class Config:
    sentry: Sentry


def config_from_env() -> Config:
    return dataconf.env("GIT_RPC_", Config)
