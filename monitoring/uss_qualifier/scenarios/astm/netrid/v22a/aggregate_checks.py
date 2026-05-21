from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.astm.f3411 import DSSInstancesResource
from monitoring.uss_qualifier.resources.dev import TestExclusionsResource
from monitoring.uss_qualifier.resources.netrid import (
    NetRIDObserversResource,
    NetRIDServiceProviders,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.common.aggregate_checks import (
    AggregateChecks as CommonAggregateChecks,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class AggregateChecks(TestScenario, CommonAggregateChecks):
    def __init__(
        self,
        service_providers: NetRIDServiceProviders,
        dss_instances: DSSInstancesResource,
        observers: NetRIDObserversResource | None = None,
        test_exclusions: TestExclusionsResource | None = None,
    ):
        super().__init__(service_providers, dss_instances, observers, test_exclusions)
        self._rid_version = RIDVersion.f3411_22a
