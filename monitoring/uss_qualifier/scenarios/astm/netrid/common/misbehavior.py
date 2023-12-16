import traceback
from typing import List, Set

import s2sphere
from requests.exceptions import RequestException
from s2sphere import LatLngRect

from monitoring.monitorlib import auth
from monitoring.monitorlib.fetch import rid
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstancesResource
from monitoring.uss_qualifier.resources.netrid import (
    FlightDataResource,
    NetRIDServiceProviders,
    EvaluationConfigurationResource,
)
from monitoring.uss_qualifier.scenarios.astm.netrid import (
    injection,
    display_data_evaluator,
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
        dss_pool: DSSInstancesResource,
    ):
        super().__init__()
        self._flights_data = flights_data
        self._service_providers = service_providers
        self._evaluation_configuration = evaluation_configuration
        if len(dss_pool.dss_instances) == 0:
            raise ValueError(
                "The Misbehavior Scenario requires at least one DSS instance"
            )
        self._dss = dss_pool.dss_instances[0]
        self._injected_tests = []

    @property
    def _rid_version(self) -> RIDVersion:
        raise NotImplementedError(
            "Misbehavior test scenario subclass must specify _rid_version"
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
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
        (self._injected_flights, self._injected_tests) = injection.inject_flights(
            self, self._flights_data, self._service_providers
        )

    def _poll_unauthenticated_during_flights(self):
        config = self._evaluation_configuration.configuration
        virtual_observer = VirtualObserver(
            injected_flights=InjectedFlightCollection(self._injected_flights),
            repeat_query_rect_period=config.repeat_query_rect_period,
            min_query_diagonal_m=config.min_query_diagonal,
            relevant_past_data_period=self._rid_version.realtime_period
            + config.max_propagation_latency.timedelta,
        )

        remaining_injection_ids = set(
            inj_flight.flight.injection_id for inj_flight in self._injected_flights
        )

        def poll_fct(rect: LatLngRect) -> bool:
            nonlocal remaining_injection_ids

            tested_inj_ids = self._evaluate_and_test_authentication(rect)
            remaining_injection_ids -= tested_inj_ids

            # interrupt polling if there are no more injection IDs to cover
            return len(remaining_injection_ids) == 0

        virtual_observer.start_polling(
            config.min_polling_interval.timedelta,
            [
                self._rid_version.max_diagonal_km * 1000 + 500,  # too large
                self._rid_version.max_diagonal_km * 1000 - 100,  # clustered
                self._rid_version.max_details_diagonal_km * 1000 - 100,  # details
            ],
            poll_fct,
        )

    def _evaluate_and_test_authentication(
        self,
        rect: s2sphere.LatLngRect,
    ) -> Set[str]:
        """Queries all flights in the expected way, then repeats the queries to SPs without credentials.

        returns true once queries to SPS have been made without credentials. False otherwise, such as when
        no flights were yet returned by the authenticated queries.

        :returns: set of injection IDs that were encountered and tested
        """

        # We grab all flights from the SP's (which we know how to reach by first querying the DSS).
        # This is authenticated and is expected to succeed
        sp_observation = rid.all_flights(
            rect,
            include_recent_positions=True,
            get_details=True,
            rid_version=self._rid_version,
            session=self._dss.client,
            dss_participant_id=self._dss.participant_id,
        )

        mapping_by_injection_id = (
            display_data_evaluator.map_fetched_to_injected_flights(
                self._injected_flights, list(sp_observation.uss_flight_queries.values())
            )
        )
        for q in sp_observation.queries:
            self.record_query(q)

        for injection_id, mapping in mapping_by_injection_id.items():
            participant_id = mapping.injected_flight.uss_participant_id
            flights_url = mapping.observed_flight.query.flights_url
            unauthenticated_session = UTMClientSession(
                flights_url, auth.NoAuth(aud_override="")
            )

            self.record_note(
                f"{participant_id}/{injection_id}/missing_credentials_queries",
                f"Will attempt querying with missing credentials at flights URL {flights_url} for a flights list and {len(mapping.observed_flight.query.flights)} flight details.",
            )

            with self.check("Missing credentials", [participant_id]) as check:

                # check uss flights query
                uss_flights_query = rid.uss_flights(
                    flights_url,
                    rect,
                    True,
                    self._rid_version,
                    unauthenticated_session,
                    participant_id,
                )
                self.record_query(uss_flights_query.query)

                if uss_flights_query.success:
                    check.record_failed(
                        "Unauthenticated request for flights to USS was fulfilled",
                        severity=Severity.Medium,
                        details=f"Queried flights on {flights_url} for USS {participant_id} with no credentials, expected a failure but got a success reply.",
                    )
                elif uss_flights_query.status_code != 401:
                    check.record_failed(
                        "Unauthenticated request for flights failed with wrong HTTP code",
                        severity=Severity.Medium,
                        details=f"Queried flights on {flights_url} for USS {participant_id} with no credentials, expected an HTTP 401 but got an HTTP {uss_flights_query.status_code}.",
                    )

                # check flight details query
                for flight in mapping.observed_flight.query.flights:
                    uss_flight_details_query = rid.flight_details(
                        flights_url,
                        flight.id,
                        False,
                        self._rid_version,
                        unauthenticated_session,
                        participant_id,
                    )
                    self.record_query(uss_flight_details_query.query)

                    if uss_flight_details_query.success:
                        check.record_failed(
                            "Unauthenticated request for flight details to USS was fulfilled",
                            severity=Severity.Medium,
                            details=f"Queried flight details on {flights_url} for USS {participant_id} for flight {flight.id} with no credentials, expected a failure but got a success reply.",
                        )
                    elif uss_flight_details_query.status_code != 401:
                        check.record_failed(
                            "Unauthenticated request for flight details failed with wrong HTTP code",
                            severity=Severity.Medium,
                            details=f"Queried flight details on {flights_url} for USS {participant_id} for flight {flight.id} with no credentials, expected an HTTP 401 but got an HTTP {uss_flight_details_query.status_code}.",
                        )

        return set(mapping_by_injection_id.keys())

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
