from typing import List, Optional

from requests.exceptions import RequestException
from s2sphere import LatLngRect

from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstancesResource
from monitoring.uss_qualifier.resources.netrid import (
    FlightDataResource,
    NetRIDServiceProviders,
    NetRIDObserversResource,
    EvaluationConfigurationResource,
)
from monitoring.uss_qualifier.scenarios.astm.netrid import (
    display_data_evaluator,
    injection,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.injected_flight_collection import (
    InjectedFlightCollection,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.injection import (
    InjectedFlight,
    InjectedTest,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.virtual_observer import (
    VirtualObserver,
)
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class ServiceProviderNotifiesSlowUpdates(GenericTestScenario):
    def __init__(
        self,
        flights_data: FlightDataResource,
        service_providers: NetRIDServiceProviders,
        evaluation_configuration: EvaluationConfigurationResource,  # TODO confirm if needed
        dss_pool: DSSInstancesResource,
    ):
        super().__init__()

    @property
    def _rid_version(self) -> RIDVersion:
        raise NotImplementedError(
            "ServiceProviderNotifiesSlowUpdates test scenario subclass must specify _rid_version"
        )

    def run(self, context: ExecutionContext):
        pass
