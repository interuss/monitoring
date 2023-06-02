from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.astm.netrid.common.nominal_behavior import (
    NominalBehavior as CommonNominalBehavior,
)


class NominalBehavior(TestScenario, CommonNominalBehavior):
    pass
