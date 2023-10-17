import time
import traceback
import uuid
from datetime import timedelta
from typing import List, Optional, Tuple

import arrow
from implicitdict import ImplicitDict
from loguru import logger
from requests.exceptions import RequestException
from uas_standards.interuss.automated_testing.rid.v1.injection import ChangeTestResponse

from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.rid_automated_testing.injection_api import (
    CreateTestParameters,
)
from monitoring.monitorlib.rid_automated_testing.injection_api import TestFlight
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstancesResource
from monitoring.uss_qualifier.resources.netrid import (
    FlightDataResource,
    NetRIDServiceProviders,
    NetRIDObserversResource,
    EvaluationConfigurationResource,
)
from monitoring.uss_qualifier.scenarios.astm.netrid import display_data_evaluator
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
from monitoring.uss_qualifier.scenarios.scenario import (
    GenericTestScenario,
    TestScenario,
)


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
        self._injected_flights = []
        self._injected_tests = []
        self._dss_pool = dss_pool

    @property
    def _rid_version(self) -> RIDVersion:
        raise NotImplementedError(
            "NominalBehavior test scenario subclass must specify _rid_version"
        )

    def run(self):
        self.begin_test_scenario()
        self.begin_test_case("Nominal flight")

        self.begin_test_step("Injection")
        self._inject_flights()
        self.end_test_step()

        self._poll_during_flights()

        self.end_test_case()
        self.end_test_scenario()

    def _inject_flights(self):
        (self._injected_flights, self._injected_tests) = inject_flights(
            test_scenario=self,
            flights_data=self._flights_data,
            service_providers=self._service_providers,
            evaluation_configuration=self._evaluation_configuration,
            realtime_period=self._rid_version.realtime_period,
        )

    def _poll_during_flights(self):
        config = self._evaluation_configuration.configuration

        # Evaluate observed RID system states
        evaluator = display_data_evaluator.RIDObservationEvaluator(
            self,
            self._injected_flights,
            config,
            self._rid_version,
            self._dss_pool.dss_instances[0] if self._dss_pool else None,
        )

        t_end = self._virtual_observer.get_last_time_of_interest()
        t_now = arrow.utcnow()
        if t_now > t_end:
            raise RuntimeError(
                f"Cannot evaluate RID system: injected test flights ended at {t_end}, which is before now ({t_now})"
            )

        logger.debug(f"Polling from {t_now} until {t_end}")
        for f in self._injected_flights:
            span = f.flight.get_span()
            logger.debug(
                f"Flight {f.uss_participant_id}/{f.flight.injection_id} {span[0].isoformat()} to {span[1].isoformat()}",
            )

        t_next = arrow.utcnow()
        dt = config.min_polling_interval.timedelta
        while arrow.utcnow() < t_end:
            # Evaluate the system at an instant in time for various areas
            diagonals_m = [
                self._rid_version.max_diagonal_km * 1000 + 500,  # too large
                self._rid_version.max_diagonal_km * 1000 - 100,  # clustered
                self._rid_version.max_details_diagonal_km * 1000 - 100,  # details
            ]
            for diagonal_m in diagonals_m:
                rect = self._virtual_observer.get_query_rect(diagonal_m)
                evaluator.evaluate_system_instantaneously(
                    self._observers.observers, rect
                )

            # Wait until minimum polling interval elapses
            while t_next < arrow.utcnow():
                t_next += dt
            if t_next > t_end:
                break
            delay = t_next - arrow.utcnow()
            if delay.total_seconds() > 0:
                logger.debug(
                    f"Waiting {delay.total_seconds()} seconds before polling RID system again..."
                )
                time.sleep(delay.total_seconds())

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
                stacktrace = "".join(
                    traceback.format_exception(type(e), value=e, tb=e.__traceback__)
                )
                check.record_failed(
                    summary="Error while trying to delete test flight",
                    severity=Severity.Medium,
                    details=f"While trying to delete a test flight from {sp.participant_id}, encountered error:\n{stacktrace}",
                )
        self.end_cleanup()


def inject_flights(
    test_scenario: TestScenario,
    flights_data: FlightDataResource,
    service_providers: NetRIDServiceProviders,
    evaluation_configuration: EvaluationConfigurationResource,
    realtime_period: timedelta,
) -> Tuple[List[InjectedFlight], List[InjectedTest]]:
    test_id = str(uuid.uuid4())
    test_flights = flights_data.get_test_flights()
    service_providers = service_providers.service_providers

    injected_flights: List[InjectedFlight] = []
    injected_tests: List[InjectedTest] = []

    if len(service_providers) > len(test_flights):
        raise ValueError(
            "{} service providers were specified, but data for only {} test flights were provided".format(
                len(service_providers), len(test_flights)
            )
        )
    for i, target in enumerate(service_providers):
        p = CreateTestParameters(requested_flights=[test_flights[i]])
        check = test_scenario.check("Successful injection", [target.participant_id])
        try:
            query = target.submit_test(p, test_id)
        except RequestException as e:
            stacktrace = "".join(
                traceback.format_exception(type(e), value=e, tb=e.__traceback__)
            )
            check.record_failed(
                summary="Error while trying to inject test flight",
                severity=Severity.High,
                details=f"While trying to inject a test flight into {target.participant_id}, encountered error:\n{stacktrace}",
            )
            raise RuntimeError("High-severity issue did not abort test scenario")
        test_scenario.record_query(query)
        try:
            if query.status_code != 200:
                raise ValueError(
                    f"Expected response code 200 but received {query.status_code} instead"
                )
            if "json" not in query.response:
                raise ValueError("Response did not contain a JSON body")
            changed_test: ChangeTestResponse = ImplicitDict.parse(
                query.response.json, ChangeTestResponse
            )
            injected_tests.append(
                InjectedTest(
                    participant_id=target.participant_id,
                    test_id=test_id,
                    version=changed_test.version,
                )
            )
            injections = changed_test.injected_flights
            check.record_passed()
        except ValueError as e:
            check.record_failed(
                summary="Error injecting test flight",
                severity=Severity.High,
                details=f"Attempting to inject a test flight into {target.participant_id}, encountered status code {query.status_code}: {str(e)}",
                query_timestamps=[query.request.timestamp],
            )
            raise RuntimeError("High-severity issue did not abort test scenario")

        start_time = None
        end_time = None
        for flight in injections:
            injected_flights.append(
                InjectedFlight(
                    uss_participant_id=target.participant_id,
                    test_id=test_id,
                    flight=TestFlight(flight),
                    query_timestamp=query.request.timestamp,
                )
            )
            earliest_time = min(t.timestamp.datetime for t in flight.telemetry)
            latest_time = max(t.timestamp.datetime for t in flight.telemetry)
            if start_time is None or earliest_time < start_time:
                start_time = earliest_time
            if end_time is None or latest_time > end_time:
                end_time = latest_time
        now = arrow.utcnow().datetime
        dt0 = (start_time - now).total_seconds()
        dt1 = (end_time - now).total_seconds()
        test_scenario.record_note(
            f"{test_id} time range",
            f"Injected flights start {dt0:.1f} seconds from now and end {dt1:.1f} seconds from now",
        )

    # Make sure the injected flights can be identified correctly by the test harness
    with test_scenario.check("Identifiable flights") as check:
        errors = display_data_evaluator.injected_flights_errors(injected_flights)
        if errors:
            check.record_failed(
                "Injected flights not suitable for test",
                Severity.High,
                details="When checking the suitability of the flights (as injected) for the test, found:\n"
                + "\n".join(errors),
                query_timestamps=[f.query_timestamp for f in injected_flights],
            )
            raise RuntimeError("High-severity issue did not abort test scenario")

    config = evaluation_configuration.configuration
    test_scenario._virtual_observer = VirtualObserver(
        injected_flights=InjectedFlightCollection(injected_flights),
        repeat_query_rect_period=config.repeat_query_rect_period,
        min_query_diagonal_m=config.min_query_diagonal,
        relevant_past_data_period=realtime_period
        + config.max_propagation_latency.timedelta,
    )
    return injected_flights, injected_tests
