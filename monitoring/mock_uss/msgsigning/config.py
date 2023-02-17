from monitoring.mock_uss import import_environment_variable


KEY_CERT_BASE_PATH = "MOCK_USS_CERT_BASE_PATH"

import_environment_variable(KEY_CERT_BASE_PATH, default="/var/test-certs")
