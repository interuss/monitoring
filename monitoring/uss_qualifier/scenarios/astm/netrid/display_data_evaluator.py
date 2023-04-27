from dataclasses import dataclass
from typing import List, Optional, Dict, Union, Set

import arrow
from loguru import logger
import math
import s2sphere

from monitoring.monitorlib.fetch import Query
from monitoring.monitorlib.fetch.rid import (
    all_flights,
    FetchedFlights,
    FetchedUSSFlights,
    Position,
)
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstance
from uas_standards.interuss.automated_testing.rid.v1.injection import RIDAircraftState
from uas_standards.interuss.automated_testing.rid.v1.observation import (
    Flight,
    GetDisplayDataResponse,
)

from monitoring.monitorlib import fetch, geo, schema_validation
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.resources.netrid.observers import RIDSystemObserver
from monitoring.uss_qualifier.scenarios.astm.netrid.injected_flight_collection import (
    InjectedFlightCollection,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.virtual_observer import (
    VirtualObserver,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from monitoring.uss_qualifier.scenarios.astm.netrid.injection import InjectedFlight


DISTANCE_TOLERANCE_M = 0.01
COORD_TOLERANCE_DEG = 360 / geo.EARTH_CIRCUMFERENCE_M * DISTANCE_TOLERANCE_M


def _rect_str(rect) -> str:
    return "({}, {})-({}, {})".format(
        rect.lo().lat().degrees,
        rect.lo().lng().degrees,
        rect.hi().lat().degrees,
        rect.hi().lng().degrees,
    )


def _telemetry_match(t1: RIDAircraftState, t2: RIDAircraftState) -> bool:
    """Determine whether two telemetry points may be mistaken for each other."""
    return (
        abs(t1.position.lat - t2.position.lat) < COORD_TOLERANCE_DEG
        and abs(t1.position.lng == t2.position.lng) < COORD_TOLERANCE_DEG
    )


def injected_flights_errors(injected_flights: List[InjectedFlight]) -> List[str]:
    """Determine whether each telemetry in each injected flight can be easily distinguished from each other.

    Args:
        injected_flights: Full set of flights injected into Service Providers.

    Returns: List of error messages, or an empty list if no errors.
    """
    errors: List[str] = []
    for f1, injected_flight in enumerate(injected_flights):
        for t1, injected_telemetry in enumerate(injected_flight.flight.telemetry):
            for t2, other_telmetry in enumerate(
                injected_flight.flight.telemetry[t1 + 1 :]
            ):
                if _telemetry_match(injected_telemetry, other_telmetry):
                    errors.append(
                        f"{injected_flight.uss_participant_id}'s flight with injection ID {injected_flight.flight.injection_id} in test {injected_flight.test_id} has telemetry at indices {t1} and {t1 + 1 + t2} which can be mistaken for each other"
                    )
            for f2, other_flight in enumerate(injected_flights[f1 + 1 :]):
                for t2, other_telemetry in enumerate(other_flight.flight.telemetry):
                    if _telemetry_match(injected_telemetry, other_telemetry):
                        errors.append(
                            f"{injected_flight.uss_participant_id}'s flight with injection ID {injected_flight.flight.injection_id} in test {injected_flight.test_id} has telemetry at index {t1} that can be mistaken for telemetry index {t2} in {other_flight.uss_participant_id}'s flight with injection ID {other_flight.flight.injection_id} in test {other_flight.test_id}"
                        )
    return errors


@dataclass
class DPObservedFlight(object):
    query: FetchedUSSFlights
    flight: int

    @property
    def id(self) -> str:
        return self.query.flights[self.flight].id

    @property
    def most_recent_position(self) -> Optional[Position]:
        return self.query.flights[self.flight].most_recent_position


ObservationType = Union[Flight, DPObservedFlight]


@dataclass
class TelemetryMapping(object):
    injected_flight: InjectedFlight
    telemetry_index: int
    observed_flight: ObservationType


def _make_flight_mapping(
    injected_flights: List[InjectedFlight],
    observed_flights: List[ObservationType],
) -> Dict[str, TelemetryMapping]:
    """Identify which of the observed flights (if any) matches to each of the injected flights

    This function assumes there is no valid situation in which a particular observed flight could be one of multiple
    InjectedFlights; the 3D position of each telemetry point in each InjectedFlight may not be duplicated in any other
    telemetry point in any InjectedFlight.  This assumption is checked by injected_flights_errors.

    Args:
        injected_flights: Flights injected into RID Service Providers under test.
        observed_flights: Flight observed from an RID Display Provider under test.

    Returns: Mapping betweenInjectedFlight and observed Flight, indexed by injection_id.
    """
    mapping: Dict[str, TelemetryMapping] = {}
    for injected_flight in injected_flights:
        smallest_distance = 1e9
        best_match = None
        for observed_flight in observed_flights:
            if (
                isinstance(observed_flight, Flight)
                and "most_recent_position" not in observed_flight
            ):
                logger.warning(
                    "observed_flight {} is missing most_recent_position",
                    observed_flight.id,
                )
                continue
            p = observed_flight.most_recent_position
            if p is None:
                logger.warning(
                    "most_recent_position is None in observed_flight {}",
                    observed_flight.id,
                )
                continue
            for t1, injected_telemetry in enumerate(injected_flight.flight.telemetry):
                dlat = abs(p.lat - injected_telemetry.position.lat)
                dlng = abs(p.lng - injected_telemetry.position.lng)
                if dlat < COORD_TOLERANCE_DEG and dlng < COORD_TOLERANCE_DEG:
                    new_distance = math.sqrt(math.pow(dlat, 2) + math.pow(dlng, 2))
                    if new_distance < smallest_distance:
                        best_match = TelemetryMapping(
                            injected_flight=injected_flight,
                            telemetry_index=t1,
                            observed_flight=observed_flight,
                        )
                        smallest_distance = new_distance
        if best_match is not None:
            observed_p = best_match.observed_flight.most_recent_position
            observed_lat = observed_p.lat if "lat" in observed_p else None
            observed_lng = observed_p.lng if "lng" in observed_p else None
            observed_alt = observed_p.alt if "alt" in observed_p else None
            best_p = best_match.injected_flight.flight.telemetry[
                best_match.telemetry_index
            ].position
            best_lat = best_p.lat if "lat" in best_p else None
            best_lng = best_p.lng if "lng" in best_p else None
            best_alt = best_p.alt if "alt" in best_p else None
            logger.debug(
                f"For injection ID {best_match.injected_flight.flight.injection_id}, matched observed flight {best_match.observed_flight.id} at ({observed_lat}, {observed_lng})+{observed_alt} to injected flight's telemetry index {best_match.telemetry_index} at ({best_lat}, {best_lng})+{best_alt}"
            )
            mapping[best_match.injected_flight.flight.injection_id] = best_match
    return mapping


class RIDObservationEvaluator(object):
    """Evaluates observations of an RID system over time.

    This evaluator observes a set of provided RIDSystemObservers in
    evaluate_system by repeatedly polling them according to the expected data
    provided to RIDObservationEvaluator upon construction.  During these
    evaluations, RIDObservationEvaluator mutates provided findings object to add
    additional findings.
    """

    def __init__(
        self,
        test_scenario: TestScenarioType,
        injected_flights: List[InjectedFlight],
        config: EvaluationConfiguration,
        rid_version: RIDVersion,
        dss: Optional[DSSInstance] = None,
    ):
        self._test_scenario = test_scenario
        self._injected_flights = injected_flights
        self._virtual_observer = VirtualObserver(
            injected_flights=InjectedFlightCollection(injected_flights),
            repeat_query_rect_period=config.repeat_query_rect_period,
            min_query_diagonal_m=config.min_query_diagonal,
            relevant_past_data_period=rid_version.realtime_period
            + config.max_propagation_latency.timedelta,
        )
        self._config = config
        self._rid_version = rid_version
        self._dss = dss
        if dss and dss.rid_version != rid_version:
            raise ValueError(
                f"Cannot evaluate a system using RID version {rid_version} with a DSS using RID version {dss.rid_version}"
            )

    def evaluate_system_instantaneously(
        self,
        observers: List[RIDSystemObserver],
        rect: s2sphere.LatLngRect,
    ) -> None:
        if self._dss:
            self._test_scenario.begin_test_step("Service Provider polling")

            # Observe Service Provider with uss_qualifier acting as a Display Provider
            sp_observation = all_flights(
                rect,
                include_recent_positions=True,
                get_details=True,
                rid_version=self._rid_version,
                session=self._dss.client,
            )
            for q in sp_observation.queries:
                self._test_scenario.record_query(q)

            self._evaluate_sp_observation(sp_observation, rect)

            step_report = self._test_scenario.end_test_step()
            perform_observation = step_report.successful()
            verified_sps = {
                obs.participant_id
                for obs in observers
                if obs.participant_id
                not in step_report.participants_with_failed_checks()
            }
        else:
            perform_observation = True
            verified_sps = set()

        if perform_observation:
            self._test_scenario.begin_test_step("Observer polling")
            for observer in observers:
                (observation, query) = observer.observe_system(rect)
                self._test_scenario.record_query(query)
                self._evaluate_observation(
                    observer,
                    rect,
                    observation,
                    query,
                    verified_sps,
                )

                # TODO: If bounding rect is smaller than cluster threshold, expand slightly above cluster threshold and re-observe
                # TODO: If bounding rect is smaller than area-too-large threshold, expand slightly above area-too-large threshold and re-observe
            self._test_scenario.end_test_step()

    def _evaluate_observation(
        self,
        observer: RIDSystemObserver,
        rect: s2sphere.LatLngRect,
        observation: Optional[GetDisplayDataResponse],
        query: fetch.Query,
        verified_sps: Set[str],
    ) -> None:
        diagonal_km = (
            rect.lo().get_distance(rect.hi()).degrees * geo.EARTH_CIRCUMFERENCE_KM / 360
        )
        if diagonal_km > self._rid_version.max_diagonal_km:
            self._evaluate_area_too_large_observation(
                observer, rect, diagonal_km, query
            )
        elif diagonal_km > self._rid_version.max_details_diagonal_km:
            self._evaluate_clusters_observation()
        else:
            self._evaluate_normal_observation(
                observer,
                rect,
                observation,
                query,
                verified_sps,
            )

    def _evaluate_normal_observation(
        self,
        observer: RIDSystemObserver,
        rect: s2sphere.LatLngRect,
        observation: Optional[GetDisplayDataResponse],
        query: fetch.Query,
        verified_sps: Set[str],
    ) -> None:
        with self._test_scenario.check(
            "Successful observation", [observer.participant_id]
        ) as check:
            if observation is None:
                check.record_failed(
                    summary="Observation failed",
                    details=f"When queried for an observation in {_rect_str(rect)}, {observer.participant_id} returned code {query.status_code}",
                    severity=Severity.Medium,
                    query_timestamps=[query.request.timestamp],
                )
                return
            else:
                check.record_passed()

        # Make sure we didn't get duplicate flight IDs
        flights_by_id = {}
        for observed_flight in observation.flights:
            flights_by_id[observed_flight.id] = (
                flights_by_id.get(observed_flight.id, 0) + 1
            )
        with self._test_scenario.check(
            "Duplicate flights", [observer.participant_id]
        ) as check:
            duplicates = [f"{k} ({v})" for k, v in flights_by_id.items() if v > 1]
            if duplicates:
                check.record_failed(
                    "Duplicate flight IDs in observation",
                    Severity.Medium,
                    details="Duplicate flight IDs observed: " + ", ".join(duplicates),
                    query_timestamps=[query.request.timestamp],
                )

        mapping_by_injection_id = _make_flight_mapping(
            self._injected_flights, observation.flights
        )

        self._evaluate_flight_presence(
            observer.participant_id,
            [query],
            True,
            mapping_by_injection_id,
            verified_sps,
        )

        # Check that altitudes match for any observed flights matching injected flights
        for mapping in mapping_by_injection_id.values():
            injected_telemetry = mapping.injected_flight.flight.telemetry[
                mapping.telemetry_index
            ]
            observed_position = mapping.observed_flight.most_recent_position
            injected_position = injected_telemetry.position
            if "alt" in observed_position:
                with self._test_scenario.check(
                    "Observed altitude",
                    [
                        observer.participant_id,
                        mapping.injected_flight.uss_participant_id,
                    ],
                ) as check:
                    if (
                        abs(observed_position.alt - injected_position.alt)
                        > DISTANCE_TOLERANCE_M
                    ):
                        check.record_failed(
                            "Observed altitude does not match injected altitude",
                            Severity.Medium,
                            details=f"{mapping.injected_flight.uss_participant_id}'s flight with injection ID {mapping.injected_flight.flight.injection_id} in test {mapping.injected_flight.test_id} had telemetry index {mapping.telemetry_index} at {injected_telemetry.timestamp} with lat={injected_telemetry.position.lat}, lng={injected_telemetry.position.lng}, alt={injected_telemetry.position.alt}, but {observer.participant_id} observed lat={observed_position.lat}, lng={observed_position.lng}, alt={observed_position.alt} at {query.request.initiated_at}",
                        )

    def _evaluate_flight_presence(
        self,
        observer_participant_id: str,
        observation_queries: List[Query],
        observer_participant_is_relevant: bool,
        mapping_by_injection_id: Dict[str, TelemetryMapping],
        verified_sps: Set[str],
    ):
        query_timestamps = [q.request.timestamp for q in observation_queries]
        observer_participants = (
            [observer_participant_id] if observer_participant_is_relevant else []
        )
        for expected_flight in self._injected_flights:
            t_initiated = min(q.request.timestamp for q in observation_queries)
            t_response = max(q.response.reported.datetime for q in observation_queries)
            timestamps = [
                arrow.get(t.timestamp) for t in expected_flight.flight.telemetry
            ]
            t_min = min(timestamps).datetime
            t_max = max(timestamps).datetime

            if t_response < t_min:
                # This flight should definitely not have been observed (it starts in the future)
                with self._test_scenario.check(
                    "Premature flight", [expected_flight.uss_participant_id]
                ) as check:
                    if expected_flight.flight.injection_id in mapping_by_injection_id:
                        check.record_failed(
                            summary="Flight observed before it started",
                            details=f"Flight {expected_flight.flight.injection_id} injected into {expected_flight.uss_participant_id} was observed by {observer_participant_id} at {t_response.isoformat()} before that flight should have started at {t_min.isoformat()}",
                            severity=Severity.Medium,
                            query_timestamps=query_timestamps
                            + [expected_flight.query_timestamp],
                        )
                    # TODO: attempt to observe flight details
                    continue
            elif (
                t_response
                > t_max
                + self._rid_version.realtime_period
                + self._config.max_propagation_latency.timedelta
            ):
                # This flight should not have been observed (it was too far in the past)
                participants = observer_participants
                if (
                    expected_flight.uss_participant_id not in verified_sps
                    or not participants
                ):
                    participants.append(expected_flight.uss_participant_id)
                with self._test_scenario.check(
                    "Lingering flight", participants
                ) as check:
                    if expected_flight.flight.injection_id in mapping_by_injection_id:
                        check.record_failed(
                            summary="Flight still observed long after it ended",
                            details=f"Flight {expected_flight.flight.injection_id} injected into {expected_flight.uss_participant_id} was observed by {observer_participant_id} at {t_response.isoformat()} after it ended at {t_max.isoformat()}",
                            severity=Severity.Medium,
                            query_timestamps=query_timestamps
                            + [expected_flight.query_timestamp],
                        )
                        continue
            elif (
                t_min + self._config.max_propagation_latency.timedelta
                < t_initiated
                < t_max
                + self._rid_version.realtime_period
                - self._config.max_propagation_latency.timedelta
            ):
                # This flight should definitely have been observed
                participants = observer_participants
                if (
                    expected_flight.uss_participant_id not in verified_sps
                    or not participants
                ):
                    participants.append(expected_flight.uss_participant_id)
                with self._test_scenario.check("Missing flight", participants) as check:
                    if (
                        expected_flight.flight.injection_id
                        not in mapping_by_injection_id
                    ):
                        check.record_failed(
                            summary="Expected flight not observed",
                            details=f"Flight {expected_flight.flight.injection_id} injected into {expected_flight.uss_participant_id} was not found in the observation by {observer_participant_id} at {t_response.isoformat()} even though it should have been active from {t_min.isoformat()} to {t_max.isoformat()}",
                            severity=Severity.Medium,
                            query_timestamps=query_timestamps
                            + [expected_flight.query_timestamp],
                        )
                        continue
                # TODO: observe flight details
            elif t_initiated > t_min:
                # If this flight was not observed, there may be propagation latency
                pass  # TODO: findings propagation latency

    def _evaluate_area_too_large_observation(
        self,
        observer: RIDSystemObserver,
        rect: s2sphere.LatLngRect,
        diagonal: float,
        query: fetch.Query,
    ) -> None:
        with self._test_scenario.check(
            "Area too large", [observer.participant_id]
        ) as check:
            if query.status_code != 413:
                check.record_failed(
                    summary="Did not receive expected error code for too-large area request",
                    details=f"{observer.participant_id} was queried for flights in {_rect_str(rect)} with a diagonal of {diagonal} which is larger than the maximum allowed diagonal of {self._rid_version.max_diagonal_km}.  The expected error code is 413, but instead code {query.status_code} was received.",
                    severity=Severity.High,
                    query_timestamps=[query.request.timestamp],
                )

    def _evaluate_clusters_observation(self) -> None:
        # TODO: Check cluster sizing, aircraft counts, etc
        pass

    def _evaluate_sp_observation(
        self,
        sp_observation: FetchedFlights,
        rect: s2sphere.LatLngRect,
    ) -> None:
        # Note: This step currently uses the DSS endpoint to perform a one-time query for ISAs, but this
        # endpoint is not strictly required.  The PUT Subscription endpoint, followed immediately by the
        # DELETE Subscription would produce the same result, but because uss_qualifier does not expose any
        # endpoints (and therefore cannot provide a callback/base URL), calling the one-time query endpoint
        # is currently much cleaner.  If this test is applied to a DSS that does not implement the one-time
        # ISA query endpoint, this check can be adapted.
        with self._test_scenario.check("ISA query") as check:
            if not sp_observation.dss_isa_query.success:
                check.record_failed(
                    summary="Could not query ISAs from DSS",
                    severity=Severity.Medium,
                    details=f"Query to {self._dss.participant_id}'s DSS at {sp_observation.dss_isa_query.query.request.url} failed {sp_observation.dss_isa_query.query.status_code}",
                    participants=[self._dss.participant_id],
                    query_timestamps=[
                        sp_observation.dss_isa_query.query.request.initiated_at.datetime
                    ],
                )
                return

        observed_flights = []
        for uss_query in sp_observation.uss_flight_queries.values():
            for f in range(len(uss_query.flights)):
                observed_flights.append(DPObservedFlight(query=uss_query, flight=f))
        mapping_by_injection_id = _make_flight_mapping(
            self._injected_flights, observed_flights
        )

        diagonal_km = (
            rect.lo().get_distance(rect.hi()).degrees * geo.EARTH_CIRCUMFERENCE_KM / 360
        )
        if diagonal_km > self._rid_version.max_diagonal_km:
            self._evaluate_area_too_large_sp_observation(
                mapping_by_injection_id, rect, diagonal_km
            )
        else:
            self._evaluate_normal_sp_observation(
                sp_observation, mapping_by_injection_id
            )

    def _evaluate_normal_sp_observation(
        self,
        sp_observation: FetchedFlights,
        mappings: Dict[str, TelemetryMapping],
    ) -> None:

        self._evaluate_flight_presence(
            "uss_qualifier, acting as Display Provider",
            sp_observation.queries,
            False,
            mappings,
            set(),
        )

        # Verify that flights queries returned correctly-formatted data
        for mapping in mappings.values():
            flights_queries = [
                q
                for flight_url, q in sp_observation.uss_flight_queries.items()
                if mapping.observed_flight.id in {f.id for f in q.flights}
            ]
            if len(flights_queries) != 1:
                raise RuntimeError(
                    f"Found {len(flights_queries)} flights queries (instead of the expected 1) for flight {mapping.observed_flight.id} corresponding to injection ID {mapping.injected_flight.flight.injection_id} for {mapping.injected_flight.uss_participant_id}"
                )
            flights_query = flights_queries[0]
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_flights_response_path,
                flights_query.query.response.json,
            )
            with self._test_scenario.check(
                "Flights data format", [mapping.injected_flight.uss_participant_id]
            ) as check:
                if errors:
                    check.record_failed(
                        summary="/flights response failed schema validation",
                        severity=Severity.Medium,
                        details="The response received from querying the /flights endpoint failed validation against the required OpenAPI schema:\n"
                        + "\n".join(
                            f"At {e.json_path} in the response: {e.message}"
                            for e in errors
                        ),
                        query_timestamps=[flights_query.query.request.timestamp],
                    )

        # Check that altitudes match for any observed flights matching injected flights
        for mapping in mappings.values():
            injected_telemetry = mapping.injected_flight.flight.telemetry[
                mapping.telemetry_index
            ]
            observed_position = mapping.observed_flight.most_recent_position
            injected_position = injected_telemetry.position
            if "alt" in observed_position:
                with self._test_scenario.check(
                    "Service Provider altitude",
                    [mapping.injected_flight.uss_participant_id],
                ) as check:
                    if (
                        abs(observed_position.alt - injected_position.alt)
                        > DISTANCE_TOLERANCE_M
                    ):
                        check.record_failed(
                            "Altitude reported by Service Provider does not match injected altitude",
                            Severity.Medium,
                            details=f"{mapping.injected_flight.uss_participant_id}'s flight with injection ID {mapping.injected_flight.flight.injection_id} in test {mapping.injected_flight.test_id} had telemetry index {mapping.telemetry_index} at {injected_telemetry.timestamp} with lat={injected_telemetry.position.lat}, lng={injected_telemetry.position.lng}, alt={injected_telemetry.position.alt}, but Service Provider reported lat={observed_position.lat}, lng={observed_position.lng}, alt={observed_position.alt} at {mapping.observed_flight.query.query.request.initiated_at}",
                        )

        # Verify that flight details queries succeeded and returned correctly-formatted data
        for mapping in mappings.values():
            details_queries = [
                q
                for flight_id, q in sp_observation.uss_flight_details_queries.items()
                if flight_id == mapping.observed_flight.id
            ]
            if len(details_queries) != 1:
                raise RuntimeError(
                    f"Found {len(details_queries)} flight details queries (instead of the expected 1) for flight {mapping.observed_flight.id} corresponding to injection ID {mapping.injected_flight.flight.injection_id} for {mapping.injected_flight.uss_participant_id}"
                )
            details_query = details_queries[0]
            with self._test_scenario.check(
                "Successful flight details query",
                [mapping.injected_flight.uss_participant_id],
            ) as check:
                if not details_query.success:
                    check.record_failed(
                        summary="Flight details query not successful",
                        severity=Severity.Medium,
                        details=f"Flight details query to {details_query.query.request.url} failed {details_query.status_code}",
                        participants=[mapping.injected_flight.uss_participant_id],
                        query_timestamps=[details_query.query.request.timestamp],
                    )
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_flight_details_response_path,
                details_query.query.response.json,
            )
            with self._test_scenario.check(
                "Flight details data format",
                [mapping.injected_flight.uss_participant_id],
            ) as check:
                if errors:
                    check.record_failed(
                        summary="Flight details response failed schema validation",
                        severity=Severity.Medium,
                        details="The response received from querying the flight details endpoint failed validation against the required OpenAPI schema:\n"
                        + "\n".join(
                            f"At {e.json_path} in the response: {e.message}"
                            for e in errors
                        ),
                        query_timestamps=[details_query.query.request.timestamp],
                    )

    def _evaluate_area_too_large_sp_observation(
        self,
        mappings: Dict[str, TelemetryMapping],
        rect: s2sphere.LatLngRect,
        diagonal: float,
    ) -> None:
        for mapping in mappings.values():
            with self._test_scenario.check(
                "Area too large", [mapping.injected_flight.uss_participant_id]
            ) as check:
                check.record_failed(
                    summary="Flight discovered using too-large area request",
                    details=f"{mapping.injected_flight.uss_participant_id} was queried for flights in {_rect_str(rect)} with a diagonal of {diagonal} km which is larger than the maximum allowed diagonal of {self._rid_version.max_diagonal_km} km.  The expected error code is 413, but instead a valid response containing the expected flight was received.",
                    severity=Severity.High,
                    query_timestamps=[
                        mapping.observed_flight.query.query.request.timestamp
                    ],
                )
