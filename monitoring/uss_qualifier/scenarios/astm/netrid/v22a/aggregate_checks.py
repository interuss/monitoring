from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.interuss.report import TestSuiteReportResource
from monitoring.uss_qualifier.resources.netrid import (
    NetRIDServiceProviders,
    NetRIDObserversResource,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.common.aggregate_checks import (
    AggregateChecks as CommonAggregateChecks,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class AggregateChecks(TestScenario, CommonAggregateChecks):
    def __init__(
        self,
        report_resource: TestSuiteReportResource,
        service_providers: NetRIDServiceProviders,
        observers: NetRIDObserversResource,
    ):
        super().__init__(report_resource, service_providers, observers)
        self._rid_version = RIDVersion.f3411_22a
