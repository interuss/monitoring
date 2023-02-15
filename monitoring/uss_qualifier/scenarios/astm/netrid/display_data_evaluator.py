from dataclasses import dataclass
from typing import List, Optional, Dict

import arrow
import s2sphere

from uas_standards.astm.f3411.v19.api import RIDAircraftState
from uas_standards.interuss.automated_testing.rid.v1.observation import (
    Flight,
    GetDisplayDataResponse,
)

from monitoring.monitorlib import fetch, geo
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
class TelemetryMapping(object):
    injected_flight: InjectedFlight
    telemetry_index: int
    observed_flight: Flight


def _make_flight_mapping(
    injected_flights: List[InjectedFlight], observed_flights: List[Flight]
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
        found = False
        for observed_flight in observed_flights:
            p = observed_flight.most_recent_position
            for t1, injected_telemetry in enumerate(injected_flight.flight.telemetry):
                if (
                    abs(p.lat - injected_telemetry.position.lat) < COORD_TOLERANCE_DEG
                    and abs(p.lng - injected_telemetry.position.lng)
                    < COORD_TOLERANCE_DEG
                ):
                    mapping[injected_flight.flight.injection_id] = TelemetryMapping(
                        injected_flight=injected_flight,
                        telemetry_index=t1,
                        observed_flight=observed_flight,
                    )
                    found = True
                    break
            if found:
                break
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

    def evaluate_system_instantaneously(
        self,
        observers: List[RIDSystemObserver],
        rect: s2sphere.LatLngRect,
    ) -> None:
        for observer in observers:
            # Conduct an observation, then log and evaluate it
            (observation, query) = observer.observe_system(rect)
            self._test_scenario.record_query(query)
            self._evaluate_observation(
                observer,
                rect,
                observation,
                query,
            )

            # TODO: If bounding rect is smaller than cluster threshold, expand slightly above cluster threshold and re-observe
            # TODO: If bounding rect is smaller than area-too-large threshold, expand slightly above area-too-large threshold and re-observe

    def _evaluate_observation(
        self,
        observer: RIDSystemObserver,
        rect: s2sphere.LatLngRect,
        observation: Optional[GetDisplayDataResponse],
        query: fetch.Query,
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
            )

    def _evaluate_normal_observation(
        self,
        observer: RIDSystemObserver,
        rect: s2sphere.LatLngRect,
        observation: Optional[GetDisplayDataResponse],
        query: fetch.Query,
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

        for expected_flight in self._injected_flights:
            t_initiated = query.request.timestamp
            t_response = query.response.reported.datetime
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
                            details=f"Flight {expected_flight.flight.injection_id} injected into {expected_flight.uss_participant_id} was observed by {observer.participant_id} at {t_response.isoformat()} before that flight should have started at {t_min.isoformat()}",
                            severity=Severity.Medium,
                            query_timestamps=[
                                query.request.timestamp,
                                expected_flight.query_timestamp,
                            ],
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
                with self._test_scenario.check(
                    "Lingering flight",
                    [
                        expected_flight.uss_participant_id,
                        observer.participant_id,
                    ],
                ) as check:
                    if expected_flight.flight.injection_id in mapping_by_injection_id:
                        check.record_failed(
                            summary="Flight still observed long after it ended",
                            details=f"Flight {expected_flight.flight.injection_id} injected into {expected_flight.uss_participant_id} was observed by {observer.participant_id} at {t_response.isoformat()} after it ended at {t_max.isoformat()}",
                            severity=Severity.Medium,
                            query_timestamps=[
                                query.request.timestamp,
                                expected_flight.query_timestamp,
                            ],
                        )
                        continue
            elif (
                t_min + self._config.max_propagation_latency.timedelta
                < t_initiated
                < t_max + self._rid_version.realtime_period
            ):
                # This flight should definitely have been observed
                with self._test_scenario.check(
                    "Missing flight",
                    [
                        expected_flight.uss_participant_id,
                        observer.participant_id,
                    ],
                ) as check:
                    if (
                        expected_flight.flight.injection_id
                        not in mapping_by_injection_id
                    ):
                        check.record_failed(
                            summary="Expected flight not observed",
                            details=f"Flight {expected_flight.flight.injection_id} injected into {expected_flight.uss_participant_id} was not found in the observation by {observer.participant_id} at {t_response.isoformat()} even though it should have been active from {t_min.isoformat()} to {t_max.isoformat()}",
                            severity=Severity.Medium,
                            query_timestamps=[
                                query.request.timestamp,
                                expected_flight.query_timestamp,
                            ],
                        )
                        continue
                # TODO: observe flight details
            elif t_initiated > t_min:
                # If this flight was not observed, there may be propagation latency
                pass  # TODO: findings propagation latency

            # Check that altitudes match
            for mapping in mapping_by_injection_id.values():
                expected_telemetry = expected_flight.flight.telemetry[
                    mapping.telemetry_index
                ]
                observed_alt = mapping.observed_flight.most_recent_position.alt
                expected_alt = expected_telemetry.position.alt
                if abs(observed_alt - expected_alt) > DISTANCE_TOLERANCE_M:
                    self._test_scenario.check(
                        "Altitude",
                        [expected_flight.uss_participant_id, observer.participant_id],
                    ).record_failed(
                        "Observed altitude does not match injected altitude",
                        Severity.Medium,
                        details=f"{expected_flight.uss_participant_id}'s flight with injection ID {expected_flight.flight.injection_id} in test {expected_flight.test_id} had telemetry index {mapping.telemetry_index} at {expected_telemetry.timestamp} with lat={expected_telemetry.position.lat}, lng={expected_telemetry.position.lng}, alt={expected_telemetry.position.alt}, but {observer.participant_id} observed lat={observed_flight.most_recent_position.lat}, lng={observed_flight.most_recent_position.lng}, alt={observed_flight.most_recent_position.alt} at {query.response.reported}",
                    )

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
