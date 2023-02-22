from monitoring.mock_uss import import_environment_variable
from monitoring.monitorlib.rid import RIDVersion

KEY_RID_VERSION = "MOCK_USS_RID_VERSION"

import_environment_variable(
    KEY_RID_VERSION,
    default=RIDVersion.f3411_19,
    mutator=lambda s: RIDVersion(s),
)
