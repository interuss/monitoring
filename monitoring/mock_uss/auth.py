from monitoring.monitorlib import auth_validation
from monitoring.mock_uss import webapp
from . import config


requires_scope = auth_validation.requires_scope_decorator(
    webapp.config.get(config.KEY_TOKEN_PUBLIC_KEY),
    webapp.config.get(config.KEY_TOKEN_AUDIENCE),
)

MOCK_USS_CONFIG_SCOPE = "interuss.mock_uss.configure"
