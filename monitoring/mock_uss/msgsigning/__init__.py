from monitoring.mock_uss import config

if not config.Config.CERT_BASE_PATH:
    raise ValueError(
        f"Environment variable {config.ENV_KEY_CERT_BASE_PATH} may not be blank for the message signing functionality"
    )
