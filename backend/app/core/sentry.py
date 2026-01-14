import sentry_sdk


def init_sentry(dsn: str):
    sentry_sdk.init(dsn=dsn, traces_sample_rate=1.0, environment="production")
