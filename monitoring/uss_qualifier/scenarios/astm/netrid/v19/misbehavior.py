from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.scenarios.astm.netrid.common.misbehavior import (
    Misbehavior as CommonMisbehavior,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class Misbehavior(TestScenario, CommonMisbehavior):
    @property
    def _rid_version(self) -> RIDVersion:
        return RIDVersion.f3411_19
