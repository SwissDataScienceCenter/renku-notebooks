from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from git_services.sidecar.config import Sentry


def setup_sentry(sentry_config: "Sentry"):
    if sentry_config.enabled:
        import sentry_sdk

        sentry_sdk.init(
            dsn=sentry_config.dsn,
            environment=sentry_config.environment,
            traces_sample_rate=sentry_config.sample_rate,
        )
