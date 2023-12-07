import traceback
from typing import List, Optional

from requests.exceptions import RequestException
from s2sphere import LatLngRect

from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
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


class NominalBehavior(GenericTestScenario):
    _flights_data: FlightDataResource
    _service_providers: NetRIDServiceProviders
    _observers: NetRIDObserversResource
    _evaluation_configuration: EvaluationConfigurationResource

    _injected_flights: List[InjectedFlight]
    _injected_tests: List[InjectedTest]

    def __init__(
        self,
        flights_data: FlightDataResource,
        service_providers: NetRIDServiceProviders,
        observers: NetRIDObserversResource,
        evaluation_configuration: EvaluationConfigurationResource,
        dss_pool: Optional[DSSInstancesResource] = None,
    ):
        super().__init__()
        self._flights_data = flights_data
        self._service_providers = service_providers
        self._observers = observers
        self._evaluation_configuration = evaluation_configuration
        self._dss_pool = dss_pool
        self._injected_tests = []

    @property
    def _rid_version(self) -> RIDVersion:
        raise NotImplementedError(
            "NominalBehavior test scenario subclass must specify _rid_version"
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.begin_test_case("Nominal flight")

        self.begin_test_step("Injection")
        self._inject_flights()
        self.end_test_step()

        self._poll_during_flights()

        self.end_test_case()
        self.end_test_scenario()

    def _inject_flights(self):
        (self._injected_flights, self._injected_tests) = injection.inject_flights(
            self, self._flights_data, self._service_providers
        )

    def _poll_during_flights(self):
        config = self._evaluation_configuration.configuration
        virtual_observer = VirtualObserver(
            injected_flights=InjectedFlightCollection(self._injected_flights),
            repeat_query_rect_period=config.repeat_query_rect_period,
            min_query_diagonal_m=config.min_query_diagonal,
            relevant_past_data_period=self._rid_version.realtime_period
            + config.max_propagation_latency.timedelta,
        )
        evaluator = display_data_evaluator.RIDObservationEvaluator(
            self,
            self._injected_flights,
            config,
            self._rid_version,
            self._dss_pool.dss_instances[0] if self._dss_pool else None,
        )

        def poll_fct(rect: LatLngRect) -> bool:
            evaluator.evaluate_system_instantaneously(self._observers.observers, rect)
            return False

        virtual_observer.start_polling(
            config.min_polling_interval.timedelta,
            [
                self._rid_version.max_diagonal_km * 1000 + 500,  # too large
                self._rid_version.max_diagonal_km * 1000 - 100,  # clustered
                self._rid_version.max_details_diagonal_km * 1000 - 100,  # details
            ],
            poll_fct,
        )

    def cleanup(self):
        self.begin_cleanup()
        while self._injected_tests:
            injected_test = self._injected_tests.pop()
            matching_sps = [
                sp
                for sp in self._service_providers.service_providers
                if sp.participant_id == injected_test.participant_id
            ]
            if len(matching_sps) != 1:
                matching_ids = ", ".join(sp.participant_id for sp in matching_sps)
                raise RuntimeError(
                    f"Found {len(matching_sps)} service providers with participant ID {injected_test.participant_id} ({matching_ids}) when exactly 1 was expected"
                )
            sp = matching_sps[0]
            check = self.check("Successful test deletion", [sp.participant_id])
            try:
                query = sp.delete_test(injected_test.test_id, injected_test.version)
                self.record_query(query)
                if query.status_code != 200:
                    raise ValueError(
                        f"Received status code {query.status_code} after attempting to delete test {injected_test.test_id} at version {injected_test.version} from service provider {sp.participant_id}"
                    )
                check.record_passed()
            except (RequestException, ValueError) as e:
                stacktrace = "".join(traceback.format_exception(e))
                check.record_failed(
                    summary="Error while trying to delete test flight",
                    severity=Severity.Medium,
                    details=f"While trying to delete a test flight from {sp.participant_id}, encountered error:\n{stacktrace}",
                )
        self.end_cleanup()
