from monitoring.uss_qualifier.scenarios.interuss.evaluation_scenario import (
    ReportEvaluationScenario,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.common.aggregate_checks import (
    AggregateChecks as CommonAggregateChecks,
)


class AggregateChecks(ReportEvaluationScenario, CommonAggregateChecks):
    pass
