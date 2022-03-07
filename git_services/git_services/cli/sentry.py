from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from git_services.sidecar.config import Sentry


def setup_sentry(sentry_config: "Sentry", with_flask=False):
    if sentry_config.enabled:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=sentry_config.dsn,
            environment=sentry_config.environment,
            integrations=[FlaskIntegration()] if with_flask else [],
            traces_sample_rate=sentry_config.sample_rate,
        )
