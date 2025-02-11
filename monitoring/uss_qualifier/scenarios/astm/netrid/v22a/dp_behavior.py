from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.scenarios.astm.netrid.common.dp_behavior import (
    DisplayProviderBehavior as CommonDisplayProviderBehavior,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class DisplayProviderBehavior(TestScenario, CommonDisplayProviderBehavior):
    @property
    def _rid_version(self) -> RIDVersion:
        return RIDVersion.f3411_22a
