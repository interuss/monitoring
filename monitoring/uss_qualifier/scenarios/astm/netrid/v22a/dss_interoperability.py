from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss_interoperability import (
    DSSInteroperability as CommonDSSInteroperability,
)


class DSSInteroperability(TestScenario, CommonDSSInteroperability):
    pass
