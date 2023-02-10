from typing import List, Optional

import arrow
import s2sphere

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
from monitoring.monitorlib.rid_automated_testing import observation_api


def _rect_str(rect) -> str:
    return "({}, {})-({}, {})".format(
        rect.lo().lat().degrees,
        rect.lo().lng().degrees,
        rect.hi().lat().degrees,
        rect.hi().lng().degrees,
    )


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
        observation: Optional[observation_api.GetDisplayDataResponse],
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
        observation: Optional[observation_api.GetDisplayDataResponse],
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

        for expected_flight in self._injected_flights:
            t_initiated = query.request.timestamp
            t_response = query.response.reported.datetime
            timestamps = [
                arrow.get(t.timestamp) for t in expected_flight.flight.telemetry
            ]
            t_min = min(timestamps).datetime
            t_max = max(timestamps).datetime

            flight_id = expected_flight.flight.details_responses[
                0
            ].details.id  # TODO: Choose appropriate details rather than first
            matching_flights = [
                observed_flight
                for observed_flight in observation.flights
                if observed_flight.id == flight_id
            ]
            with self._test_scenario.check(
                "Duplicate flights", [observer.participant_id]
            ) as check:
                if len(matching_flights) > 1:
                    check.record_failed(
                        summary="Duplicate flights observed",
                        details=f'When queried for an observation in {_rect_str(rect)}, {observer.participant_id} found {len(matching_flights)} flights with flight ID "{flight_id}" that was injected into {expected_flight.uss_participant_id}',
                        severity=Severity.Medium,
                        query_timestamps=[
                            query.request.timestamp,
                            expected_flight.query_timestamp,
                        ],
                    )

            if t_response < t_min:
                # This flight should definitely not have been observed (it starts in the future)
                with self._test_scenario.check(
                    "Premature flight", [expected_flight.uss_participant_id]
                ) as check:
                    if matching_flights:
                        check.record_failed(
                            summary="Flight observed before it started",
                            details=f"Flight {flight_id} injected into {expected_flight.uss_participant_id} was observed by {observer.participant_id} at {t_response.isoformat()} before that flight should have started at {t_min.isoformat()}",
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
                    if matching_flights:
                        check.record_failed(
                            summary="Flight still observed long after it ended",
                            details=f"Flight {flight_id} injected into {expected_flight.uss_participant_id} was observed by {observer.participant_id} at {t_response.isoformat()} after it ended at {t_max.isoformat()}",
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
                    if not matching_flights:
                        check.record_failed(
                            summary="Expected flight not observed",
                            details=f"Flight {flight_id} injected into {expected_flight.uss_participant_id} was not listed in the observation by {observer.participant_id} at {t_response.isoformat()} even though it should have been active from {t_min.isoformat()} to {t_max.isoformat()}",
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

            for matching_flight in matching_flights:
                pass  # TODO: Check position, altitude, flight details, etc

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
