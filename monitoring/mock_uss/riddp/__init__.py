from . import config
from monitoring.mock_uss import webapp, require_config_value
from monitoring.mock_uss.config import KEY_DSS_URL, KEY_AUTH_SPEC
from monitoring.mock_uss.riddp.config import KEY_RID_VERSION
from monitoring.monitorlib import auth
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.rid import RIDVersion


require_config_value(KEY_DSS_URL)
require_config_value(KEY_AUTH_SPEC)
require_config_value(KEY_RID_VERSION)

if webapp.config[KEY_RID_VERSION] == RIDVersion.f3411_19:
    _dss_base_url = webapp.config[KEY_DSS_URL]
elif webapp.config[KEY_RID_VERSION] == RIDVersion.f3411_22a:
    _dss_base_url = webapp.config[KEY_DSS_URL] + "/rid/v2"
else:
    raise NotImplementedError(
        f"Cannot construct DSS base URL using RID version {webapp.config[KEY_RID_VERSION]}"
    )

utm_client = UTMClientSession(
    _dss_base_url,
    auth.make_auth_adapter(webapp.config[KEY_AUTH_SPEC]),
)
