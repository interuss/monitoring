import time
import traceback
import uuid
from typing import List

import arrow
import s2sphere
from implicitdict import ImplicitDict
from loguru import logger
from requests.exceptions import RequestException
from uas_standards.interuss.automated_testing.rid.v1.injection import ChangeTestResponse

from monitoring.monitorlib import fetch
from monitoring.monitorlib.fetch import rid
from monitoring.monitorlib.infrastructure import UTMClientSession
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
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario


class Misbehavior(GenericTestScenario):
    """
    Check that an unauthenticated client is not able to query a Service Provider
    """

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
        dss_pool: DSSInstancesResource = None,
    ):
        super().__init__()
        self._flights_data = flights_data
        self._service_providers = service_providers
        self._evaluation_configuration = evaluation_configuration
        self._injected_flights = []
        self._injected_tests = []
        if len(dss_pool.dss_instances) == 0:
            raise ValueError(
                "The Misbehavior Scenario requires at least one DSS instance"
            )
        self._dss = dss_pool.dss_instances[0]

    @property
    def _rid_version(self) -> RIDVersion:
        raise NotImplementedError(
            "Misbehavior test scenario subclass must specify _rid_version"
        )

    def run(self):
        self.begin_test_scenario()
        self.begin_test_case("Unauthenticated requests")

        self.begin_test_step("Injection")
        self._inject_flights()
        self.end_test_step()

        self.begin_test_step("Unauthenticated requests")

        self._poll_unauthenticated_during_flights()

        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _inject_flights(self):
        # TODO consider sharing code with nominal_behavior's _inject_flights
        # Inject flights into all USSs
        test_id = str(uuid.uuid4())
        test_flights = self._flights_data.get_test_flights()
        service_providers = self._service_providers.service_providers
        if len(service_providers) > len(test_flights):
            raise ValueError(
                "{} service providers were specified, but data for only {} test flights were provided".format(
                    len(service_providers), len(test_flights)
                )
            )
        for i, target in enumerate(service_providers):
            p = CreateTestParameters(requested_flights=[test_flights[i]])
            check = self.check("Successful injection", [target.participant_id])
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
            self.record_query(query)
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
                self._injected_tests.append(
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

            for flight in injections:
                self._injected_flights.append(
                    InjectedFlight(
                        uss_participant_id=target.participant_id,
                        test_id=test_id,
                        flight=TestFlight(flight),
                        query_timestamp=query.request.timestamp,
                    )
                )

        # Make sure the injected flights can be identified correctly by the test harness
        with self.check("Identifiable flights") as check:
            errors = display_data_evaluator.injected_flights_errors(
                self._injected_flights
            )
            if errors:
                check.record_failed(
                    "Injected flights not suitable for test",
                    Severity.High,
                    details="When checking the suitability of the flights (as injected) for the test, found:\n"
                    + "\n".join(errors),
                    query_timestamps=[
                        f.query_timestamp for f in self._injected_flights
                    ],
                )
                raise RuntimeError("High-severity issue did not abort test scenario")

        config = self._evaluation_configuration.configuration
        self._virtual_observer = VirtualObserver(
            injected_flights=InjectedFlightCollection(self._injected_flights),
            repeat_query_rect_period=config.repeat_query_rect_period,
            min_query_diagonal_m=config.min_query_diagonal,
            relevant_past_data_period=self._rid_version.realtime_period
            + config.max_propagation_latency.timedelta,
        )

    def _poll_unauthenticated_during_flights(self):
        config = self._evaluation_configuration.configuration

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
            auth_tests = []
            for diagonal_m in diagonals_m:
                rect = self._virtual_observer.get_query_rect(diagonal_m)
                auth_tests.append(self._evaluate_and_test_authentication(rect))

            # If we checked for all diagonals that flights queries are properly authenticated,
            # we can stop polling
            if all(auth_tests):
                logger.debug(
                    "Authentication check is complete, ending polling now.",
                )
                break

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

    def _evaluate_and_test_authentication(
        self,
        rect: s2sphere.LatLngRect,
    ) -> bool:
        """Queries all flights in the expected way, then repeats the queries to SPs without credentials.

        returns true once queries to SPS have been made without credentials. False otherwise, such as when
        no flights were yet returned by the authenticated queries.
        """

        with self.check("Missing credentials") as check:
            # We grab all flights from the SP's. This is authenticated
            # and is expected to succeed
            sp_observation = rid.all_flights(
                rect,
                include_recent_positions=True,
                get_details=True,
                rid_version=self._rid_version,
                session=self._dss.client,
            )
            # We fish out the queries that were used to grab the flights from the SP,
            # and attempt to re-query without credentials. This should fail.

            unauthenticated_session = UTMClientSession(
                prefix_url=self._dss.client.get_prefix_url(),
                auth_adapter=None,
                timeout_seconds=self._dss.client.timeout_seconds,
            )

            queries_to_repeat = list(sp_observation.uss_flight_queries.values()) + list(
                sp_observation.uss_flight_details_queries.values()
            )

            if len(queries_to_repeat) == 0:
                logger.debug("no flights queries to repeat at this point.")
                return False

            logger.debug(
                f"about to repeat {len(queries_to_repeat)} flights queries without credentials"
            )

            # Attempt to re-query the flights and flight details URLs:
            for fq in queries_to_repeat:
                failed_q = fetch.query_and_describe(
                    client=unauthenticated_session,
                    verb=fq.query.request.method,
                    url=fq.query.request.url,
                    json=fq.query.request.json,
                    data=fq.query.request.body,
                )
                logger.info(
                    f"Repeating query to {fq.query.request.url} without credentials"
                )
                server_id = fq.query.get("server_id", "unknown")
                if failed_q.response.code not in [401, 403]:
                    check.record_failed(
                        "unauthenticated request was fulfilled",
                        participants=[server_id],
                        severity=Severity.MEDIUM,
                        details=f"queried flights on {fq.query.request.url} with no credentials, expected a failure but got a success reply",
                    )
                else:
                    logger.info(
                        f"participant with id {server_id} properly authenticated the request"
                    )
                # Keep track of the failed queries, too
                self.record_query(failed_q)

            return True

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
