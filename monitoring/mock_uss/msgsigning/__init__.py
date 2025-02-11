from monitoring.mock_uss import SERVICE_MESSAGESIGNING, config

if not config.Config.CERT_BASE_PATH:
    raise ValueError(
        f"Environment variable {config.ENV_KEY_CERT_BASE_PATH} may not be blank for the {SERVICE_MESSAGESIGNING} service"
    )
