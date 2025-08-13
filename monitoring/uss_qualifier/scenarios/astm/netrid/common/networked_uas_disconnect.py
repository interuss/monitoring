from datetime import timedelta
from typing import List

from requests.exceptions import RequestException
from s2sphere import LatLngRect

from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstancesResource
from monitoring.uss_qualifier.resources.netrid import (
    EvaluationConfigurationResource,
    FlightDataResource,
    NetRIDServiceProviders,
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


class NetworkedUASDisconnect(GenericTestScenario):
    """A scenario verifying the behavior of a service provider when a networked UAS associated to it loses its connectivity."""

    _flights_data: FlightDataResource
    _service_providers: NetRIDServiceProviders
    _evaluation_configuration: EvaluationConfigurationResource

    _injected_flights: List[InjectedFlight]
    _injected_tests: List[InjectedTest]

    def __init__(
        self,
        flights_data: FlightDataResource,
        service_providers: NetRIDServiceProviders,
        evaluation_configuration: EvaluationConfigurationResource,
        dss_pool: DSSInstancesResource,
    ):
        super().__init__()
        self._flights_data = flights_data
        # Truncate flights to 15 seconds, we don't need more for this scenario,
        # (disconnection is simulated by simply not sending any data anymore)
        self._flights_data = flights_data.truncate_flights_duration(
            timedelta(seconds=15)
        )
        self._service_providers = service_providers
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
        self.begin_test_case("Networked UAS disconnect")

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

        evaluator = display_data_evaluator.DisconnectedUASObservationEvaluator(
            self,
            self._injected_flights,
            config,
            self._rid_version,
            self._dss_pool.dss_instances[0] if self._dss_pool else None,
        )

        def poll_fct(rect: LatLngRect) -> bool:
            return evaluator.evaluate_disconnected_flights(rect)

        virtual_observer.start_polling(
            config.min_polling_interval.timedelta,
            [
                self._rid_version.max_diagonal_km * 1000 - 100,  # clustered
                self._rid_version.max_details_diagonal_km * 1000 - 100,  # details
            ],
            poll_fct,
        )

        self.begin_test_step(
            "Verify all disconnected flights have been observed as disconnected"
        )
        unobserved_disconnects = evaluator.remaining_disconnections_to_observe()
        if len(unobserved_disconnects) > 0:
            with self.check(
                "All injected disconnected flights have been observed as disconnected",
                list(unobserved_disconnects.values()),
            ) as check:
                check.record_failed(
                    summary="Some disconnects were not observed",
                    details=f"The following flights have not been observed as having been disconnected despite having been observed after their last telemetry's timestamp: {list(unobserved_disconnects.keys())}",
                )
        self.end_test_step()

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
                stacktrace = stacktrace_string(e)
                check.record_failed(
                    summary="Error while trying to delete test flight",
                    details=f"While trying to delete a test flight from {sp.participant_id}, encountered error:\n{stacktrace}",
                )
        self.end_cleanup()
