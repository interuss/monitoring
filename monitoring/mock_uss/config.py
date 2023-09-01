from monitoring.mock_uss import import_environment_variable
from monitoring.monitorlib import auth_validation
from monitoring.monitorlib.locality import Locality


KEY_TOKEN_PUBLIC_KEY = "MOCK_USS_PUBLIC_KEY"
KEY_TOKEN_AUDIENCE = "MOCK_USS_TOKEN_AUDIENCE"
KEY_BASE_URL = "MOCK_USS_BASE_URL"
KEY_AUTH_SPEC = "MOCK_USS_AUTH_SPEC"
KEY_SERVICES = "MOCK_USS_SERVICES"
KEY_DSS_URL = "MOCK_USS_DSS_URL"
KEY_BEHAVIOR_LOCALITY = "MOCK_USS_BEHAVIOR_LOCALITY"
KEY_CODE_VERSION = "MONITORING_VERSION"
KEY_SAN = "MOCK_USS_SAN"
KEY_LOG_DIR = "MOCK_USS_LOG_DIR"


import_environment_variable(
    KEY_TOKEN_PUBLIC_KEY,
    default="",
    mutator=lambda s: auth_validation.fix_key(s).encode("utf-8"),
)
import_environment_variable(KEY_TOKEN_AUDIENCE, required=False)
import_environment_variable(KEY_BASE_URL, required=False)
import_environment_variable(KEY_AUTH_SPEC, required=False)
import_environment_variable(
    KEY_SERVICES,
    default="",
    mutator=lambda s: set(svc.strip().lower() for svc in s.split(",")),
)
import_environment_variable(KEY_DSS_URL, required=False)
import_environment_variable(
    KEY_BEHAVIOR_LOCALITY, default="CHE", mutator=Locality.from_locale
)
import_environment_variable(KEY_CODE_VERSION, default="Unknown")
import_environment_variable(KEY_SAN, required=False)
import_environment_variable(KEY_LOG_DIR, required=False)
