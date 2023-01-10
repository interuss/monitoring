from monitoring.mock_uss import config, SERVICE_TRACER

if not config.Config.TRACER_OPTIONS:
    raise ValueError(
        f"{config.ENV_KEY_TRACER_OPTIONS} is required for the {SERVICE_TRACER} service"
    )

if not config.Config.DSS_URL:
    raise ValueError(
        f"{config.ENV_KEY_DSS} is required for the {SERVICE_TRACER} service"
    )
