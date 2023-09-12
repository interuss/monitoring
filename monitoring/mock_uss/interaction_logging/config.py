import os.path

from monitoring.mock_uss import import_environment_variable, webapp

KEY_INTERACTIONS_LOG_DIR = "MOCK_USS_INTERACTIONS_LOG_DIR"

import_environment_variable(KEY_INTERACTIONS_LOG_DIR)

_full_path = os.path.abspath(webapp.config[KEY_INTERACTIONS_LOG_DIR])
if not os.path.exists(_full_path):
    raise ValueError(f"MOCK_USS_INTERACTIONS_LOG_DIR {_full_path} does not exist")
