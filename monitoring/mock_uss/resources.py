from monitoring.mock_uss import require_config_value, webapp
from monitoring.monitorlib import auth, infrastructure

from . import config

require_config_value(config.KEY_DSS_URL)
require_config_value(config.KEY_AUTH_SPEC)

utm_client = infrastructure.UTMClientSession(
    webapp.config[config.KEY_DSS_URL],
    auth.make_auth_adapter(webapp.config[config.KEY_AUTH_SPEC]),
)
