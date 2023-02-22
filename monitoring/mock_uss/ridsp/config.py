from monitoring.mock_uss import require_config_value
from monitoring.mock_uss.config import KEY_BASE_URL
from monitoring.mock_uss.riddp.config import KEY_RID_VERSION

require_config_value(KEY_BASE_URL)
require_config_value(KEY_RID_VERSION)
