from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.astm.f3411 import DSSInstancesResource
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
        service_providers: NetRIDServiceProviders,
        observers: NetRIDObserversResource,
        dss_instances: DSSInstancesResource,
    ):
        super().__init__(service_providers, observers, dss_instances)
        self._rid_version = RIDVersion.f3411_22a
