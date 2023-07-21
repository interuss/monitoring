from monitoring.uss_qualifier.scenarios.astm.netrid.common.aggregate_checks import (
    AggregateChecks as CommonAggregateChecks,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class AggregateChecks(TestScenario, CommonAggregateChecks):
    pass
