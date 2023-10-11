from monitoring.mock_uss import import_environment_variable
from monitoring.monitorlib import auth_validation


KEY_TOKEN_PUBLIC_KEY = "MOCK_USS_PUBLIC_KEY"
KEY_TOKEN_AUDIENCE = "MOCK_USS_TOKEN_AUDIENCE"
KEY_BASE_URL = "MOCK_USS_BASE_URL"
KEY_AUTH_SPEC = "MOCK_USS_AUTH_SPEC"
KEY_SERVICES = "MOCK_USS_SERVICES"
KEY_DSS_URL = "MOCK_USS_DSS_URL"
KEY_BEHAVIOR_LOCALITY = "MOCK_USS_BEHAVIOR_LOCALITY"
KEY_CODE_VERSION = "MONITORING_VERSION"


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
import_environment_variable(KEY_BEHAVIOR_LOCALITY, default="US.IndustryCollaboration")
import_environment_variable(KEY_CODE_VERSION, default="Unknown")
