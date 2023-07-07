from monitoring.mock_uss import import_environment_variable, require_config_value
from monitoring.mock_uss.config import KEY_DSS_URL, KEY_BASE_URL
from monitoring.monitorlib.rid import RIDVersion


KEY_TRACER_OPTIONS = "MOCK_USS_TRACER_OPTIONS"
KEY_RID_VERSION = "MOCK_USS_RID_VERSION"

import_environment_variable(KEY_TRACER_OPTIONS)
require_config_value(KEY_DSS_URL)
require_config_value(KEY_BASE_URL)
import_environment_variable(
    KEY_RID_VERSION,
    default=RIDVersion.f3411_19,
    mutator=RIDVersion,
)
