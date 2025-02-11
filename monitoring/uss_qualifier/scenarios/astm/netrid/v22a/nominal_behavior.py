from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.scenarios.astm.netrid.common.nominal_behavior import (
    NominalBehavior as CommonNominalBehavior,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class NominalBehavior(TestScenario, CommonNominalBehavior):
    @property
    def _rid_version(self) -> RIDVersion:
        return RIDVersion.f3411_22a
