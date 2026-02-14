from collections.abc import Callable
from typing import Unpack

import s2sphere
from requests.exceptions import RequestException
from s2sphere import LatLng, LatLngRect

from monitoring.monitorlib import auth, geo
from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.fetch import rid
from monitoring.monitorlib.infrastructure import UTMClientSession
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
from monitoring.uss_qualifier.scenarios.astm.netrid.display_data_evaluator import (
    FetchedToInjectedCache,
    TelemetryMapping,
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

    _injected_flights: list[InjectedFlight]
    _injected_tests: list[InjectedTest]

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
        self._query_cache = FetchedToInjectedCache()
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
        self.begin_test_case("Invalid requests")

        self.begin_test_step("Injection")
        self._inject_flights()
        self.end_test_step()

        self.begin_test_step("Invalid search area")
        self._poll_during_flights(
            [
                self._rid_version.max_diagonal_km * 1000
                - 100,  # valid diagonal required for sps urls discovery
            ],
            self._evaluate_and_test_too_large_area_requests,
            dict(),
        )
        self.end_test_step()

        self.begin_test_step("Unauthenticated requests")
        self._poll_during_flights(
            [
                self._rid_version.max_diagonal_km * 1000 + 500,  # too large
                self._rid_version.max_diagonal_km * 1000 - 100,  # clustered
                self._rid_version.max_details_diagonal_km * 1000 - 100,  # details
            ],
            self._evaluate_and_test_authentication,
            {
                "auth": auth.NoAuth(aud_override=""),
                "check_name": "Missing credentials",
                "credentials_type_description": "no",
            },
        )
        self.end_test_step()

        self.begin_test_step("Incorrectly authenticated requests")
        self._poll_during_flights(
            [
                self._rid_version.max_diagonal_km * 1000 + 500,  # too large
                self._rid_version.max_diagonal_km * 1000 - 100,  # clustered
                self._rid_version.max_details_diagonal_km * 1000 - 100,  # details
            ],
            self._evaluate_and_test_authentication,
            {
                "auth": auth.InvalidTokenSignatureAuth(),
                "check_name": "Invalid credentials",
                "credentials_type_description": "invalid",
            },
        )
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _inject_flights(self):
        (self._injected_flights, self._injected_tests) = injection.inject_flights(
            self, self._flights_data, self._service_providers
        )

    def _poll_during_flights(
        self,
        diagonals_m: list[float],
        evaluation_func: Callable[
            [LatLngRect, Unpack[dict[str, auth.AuthAdapter | str]]], set[str]
        ],
        evaluation_kwargs: dict[str, auth.AuthAdapter | str],
    ):
        """
        Poll until every injected flights have been observed.

        :param diagonals_m: List of diagonals in meters used by the virtual observer to fetch flights.
        :param evaluation_func: This method is called on each polling tick with the area to observe. It is responsible
        to fetch flights and to return the list of observed injected ids.
        """
        config = self._evaluation_configuration.configuration
        virtual_observer = VirtualObserver(
            injected_flights=InjectedFlightCollection(self._injected_flights),
            repeat_query_rect_period=config.repeat_query_rect_period,
            min_query_diagonal_m=config.min_query_diagonal,
            relevant_past_data_period=self._rid_version.realtime_period
            + config.max_propagation_latency.timedelta,
            sleep=self.sleep,
        )

        remaining_injection_ids = set(
            inj_flight.flight.injection_id for inj_flight in self._injected_flights
        )

        def poll_func(rect: LatLngRect) -> bool:
            nonlocal remaining_injection_ids

            tested_inj_ids = evaluation_func(rect, **evaluation_kwargs)
            remaining_injection_ids -= tested_inj_ids

            # interrupt polling if there are no more injection IDs to cover
            return len(remaining_injection_ids) == 0

        virtual_observer.start_polling(
            config.min_polling_interval.timedelta,
            diagonals_m,
            poll_func,
        )

    def _fetch_flights_from_dss(self, rect: LatLngRect) -> dict[str, TelemetryMapping]:
        # We grab all flights from the SPs (which we know how to reach by first querying the DSS).
        # This is authenticated and is expected to succeed
        # TODO: Add the following requests to the documentation. Possibly split it as a test step.
        sp_observation = rid.all_flights(
            rect,
            include_recent_positions=True,
            get_details=False,
            rid_version=self._rid_version,
            session=self._dss.client,
            dss_participant_id=self._dss.participant_id,
        )

        mapping_by_injection_id = (
            display_data_evaluator.map_fetched_to_injected_flights(
                self._injected_flights,
                list(sp_observation.uss_flight_queries.values()),
                self._query_cache,
            )
        )
        self.record_queries(sp_observation.queries)

        return mapping_by_injection_id

    def _evaluate_and_test_too_large_area_requests(
        self,
        rect: LatLngRect,
    ) -> set[str]:
        """Queries all flights from the DSS to discover flights urls and query them using a larger area than allowed.

        :returns: set of injection IDs that were encountered and tested
        """

        mapping_by_injection_id = self._fetch_flights_from_dss(rect)
        for injection_id, mapping in mapping_by_injection_id.items():
            self._evaluate_too_large_area(rect, injection_id, mapping)

        return set(mapping_by_injection_id.keys())

    def _evaluate_too_large_area(
        self, rect: LatLngRect, injection_id: str, mapping: TelemetryMapping
    ):
        participant_id = mapping.injected_flight.uss_participant_id
        flights_url = mapping.observed_flight.query.flights_url
        session = self._dss.client

        scale = LatLng(0.01, 0.001)
        invalid_rect = rect.expanded(scale)
        diagonal_km = geo.get_latlngrect_diagonal_km(invalid_rect)
        with self.check("Area too large", [participant_id]) as check:
            # check uss flights query
            uss_flights_query = rid.uss_flights(
                flights_url,
                invalid_rect,
                True,
                self._rid_version,
                session,
                participant_id,
            )
            self.record_query(uss_flights_query.query)

            if uss_flights_query.status_code not in (400, 413):
                check.record_failed(
                    summary="Did not receive expected error code for too-large area request",
                    details=f"{participant_id} was queried for flights in {geo.rect_str(rect)} with a diagonal of {diagonal_km} which is larger than the maximum allowed diagonal of {self._rid_version.max_diagonal_km}.  The expected error code is 400 or 413, but instead code {uss_flights_query.status_code} was received.",
                )

            if (
                uss_flights_query.flights is not None
                and len(uss_flights_query.flights) != 0
            ):
                check.record_failed(
                    summary="Received Remote ID data while an empty response was expected because the requested area was too large",
                    details=f"{participant_id} was queried for flights in {geo.rect_str(rect)} with a diagonal of {diagonal_km} which is larger than the maximum allowed diagonal of {self._rid_version.max_diagonal_km}.  The Remote ID data shall be empty, instead, the following payload was received: {uss_flights_query.query.response.content}",
                )

    def _evaluate_and_test_authentication(
        self,
        rect: s2sphere.LatLngRect,
        auth: auth.AuthAdapter,
        check_name: str,
        credentials_type_description: str,
    ) -> set[str]:
        """Queries all flights in the expected way, then repeats the queries to SPs without credentials.

        returns true once queries to SPS have been made without credentials. False otherwise, such as when
        no flights were yet returned by the authenticated queries.

        :returns: set of injection IDs that were encountered and tested
        """

        mapping_by_injection_id = self._fetch_flights_from_dss(rect)

        for injection_id, mapping in mapping_by_injection_id.items():
            participant_id = mapping.injected_flight.uss_participant_id
            flights_url = mapping.observed_flight.query.flights_url

            invalid_session = UTMClientSession(flights_url, auth)

            self.record_note(
                f"{participant_id}/{injection_id}/missing_credentials_queries",
                f"Will attempt querying with {credentials_type_description} credentials at flights URL {flights_url} for a flights list and {len(mapping.observed_flight.query.flights)} flight details.",
            )

            with self.check(check_name, [participant_id]) as check:
                # check uss flights query
                uss_flights_query = rid.uss_flights(
                    flights_url,
                    rect,
                    True,
                    self._rid_version,
                    invalid_session,
                    participant_id,
                )
                self.record_query(uss_flights_query.query)

                if uss_flights_query.success:
                    check.record_failed(
                        "Unauthenticated request for flights to USS was fulfilled",
                        details=f"Queried flights on {flights_url} for USS {participant_id} with {credentials_type_description} credentials, expected a failure but got a success reply.",
                    )
                elif uss_flights_query.status_code != 401:
                    check.record_failed(
                        "Unauthenticated request for flights failed with wrong HTTP code",
                        details=f"Queried flights on {flights_url} for USS {participant_id} with {credentials_type_description} credentials, expected an HTTP 401 but got an HTTP {uss_flights_query.status_code}.",
                    )

                # check flight details query
                for flight in mapping.observed_flight.query.flights:
                    uss_flight_details_query = rid.flight_details(
                        flights_url,
                        flight.id,
                        False,
                        self._rid_version,
                        invalid_session,
                        participant_id,
                    )
                    self.record_query(uss_flight_details_query.query)

                    if uss_flight_details_query.success:
                        check.record_failed(
                            "Unauthenticated request for flight details to USS was fulfilled",
                            details=f"Queried flight details on {flights_url} for USS {participant_id} for flight {flight.id} with {credentials_type_description} credentials, expected a failure but got a success reply.",
                        )
                    elif uss_flight_details_query.status_code != 401:
                        check.record_failed(
                            "Unauthenticated request for flight details failed with wrong HTTP code",
                            details=f"Queried flight details on {flights_url} for USS {participant_id} for flight {flight.id} with {credentials_type_description} credentials, expected an HTTP 401 but got an HTTP {uss_flight_details_query.status_code}.",
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
                stacktrace = stacktrace_string(e)
                check.record_failed(
                    summary="Error while trying to delete test flight",
                    details=f"While trying to delete a test flight from {sp.participant_id}, encountered error:\n{stacktrace}",
                )
        self.end_cleanup()
