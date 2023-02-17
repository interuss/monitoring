from monitoring.mock_uss import import_environment_variable, require_config_value
from monitoring.mock_uss.config import KEY_DSS_URL, KEY_BASE_URL


KEY_TRACER_OPTIONS = "MOCK_USS_TRACER_OPTIONS"

import_environment_variable(KEY_TRACER_OPTIONS)
require_config_value(KEY_DSS_URL)
require_config_value(KEY_BASE_URL)
