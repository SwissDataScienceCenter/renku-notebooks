from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class SentryConfig:
    """Sentry configuration."""

    enabled: Union[str, bool] = False
    dsn: Optional[str] = None
    environment: Optional[str] = None
    sample_rate: float = 0.0

    def __post_init__(self):
        if isinstance(self.enabled, str):
            # NOTE: Required because bool("False") == True and environment vars are always strings
            self.enabled = self.enabled.lower() == "true"
        # INFO: Convert empty strings to None
        for attr_name in ["dsn", "environment"]:
            attr_val = getattr(self, attr_name)
            if isinstance(attr_val, str) and len(attr_val) == 0:
                setattr(self, attr_name, None)


def setup_sentry(sentry_config: SentryConfig):
    """Initialize sentry."""
    if sentry_config.enabled:
        import sentry_sdk

        sentry_sdk.init(
            dsn=sentry_config.dsn,
            environment=sentry_config.environment,
            traces_sample_rate=sentry_config.sample_rate,
        )
