from monitoring.mock_uss.app import require_config_value, webapp
from monitoring.mock_uss.config import KEY_AUTH_SPEC, KEY_DSS_URL
from monitoring.monitorlib import auth
from monitoring.monitorlib.infrastructure import UTMClientSession

require_config_value(KEY_DSS_URL)
require_config_value(KEY_AUTH_SPEC)

utm_client = UTMClientSession(
    webapp.config[KEY_DSS_URL],
    auth.make_auth_adapter(webapp.config[KEY_AUTH_SPEC]),
)
