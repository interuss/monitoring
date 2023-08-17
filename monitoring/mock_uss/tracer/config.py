from monitoring.mock_uss import import_environment_variable, require_config_value
from monitoring.mock_uss.config import KEY_DSS_URL, KEY_BASE_URL


KEY_TRACER_OUTPUT_FOLDER = "MOCK_USS_TRACER_OUTPUT_FOLDER"
"""Environment variable containing path of folder in which to write tracer logs."""

KEY_TRACER_KML_SERVER = "MOCK_USS_TRACER_KML_SERVER"
"""Environment variable containing the base URL of the KML-generating server, if any."""

KEY_TRACER_KML_FOLDER = "MOCK_USS_TRACER_KML_FOLDER"
"""Environment variable containing the name of path on KML server, if any."""

import_environment_variable(KEY_TRACER_OUTPUT_FOLDER)
import_environment_variable(KEY_TRACER_KML_SERVER, default="")
import_environment_variable(KEY_TRACER_KML_FOLDER, default="")
require_config_value(KEY_DSS_URL)
require_config_value(KEY_BASE_URL)
