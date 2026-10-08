from datetime import UTC, datetime
from unittest.mock import MagicMock

import s2sphere
from implicitdict import StringBasedDateTime
from uas_standards.interuss.automated_testing.rid.v1 import injection, observation

from monitoring.monitorlib.fetch import Query, RequestDescription, ResponseDescription
from monitoring.monitorlib.fetch.rid import FetchedFlights, FetchedISAs, Flight
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.scenarios.astm.netrid.common_dictionary_evaluator_test import (
    mock_flight,
    to_positions,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.display_data_evaluator import (
    RIDObservationEvaluator,
    check_fetched_flights,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.injection import InjectedFlight
from monitoring.uss_qualifier.scenarios.interuss.unit_test import UnitTestScenario
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario


# This test is AI-generated and has not been closely inspected by a human.
def test_failed_dss_search_records_query_timestamp():
    now = datetime(2026, 10, 7, tzinfo=UTC)
    query = Query(
        request=RequestDescription(
            method="GET",
            url="https://dss.example/isas",
            initiated_at=StringBasedDateTime(now),
        ),
        response=ResponseDescription(
            code=500, reported=StringBasedDateTime(now), elapsed_s=0
        ),
    )
    fetched = FetchedFlights(
        dss_isa_query=FetchedISAs(v22a_query=query),
        uss_flight_queries={},
        uss_flight_details_queries={},
    )
    scenario = MagicMock(spec=GenericTestScenario)

    check_fetched_flights(fetched, scenario, "dss", False)

    check = scenario.check.return_value.__enter__.return_value
    check.record_failed.assert_called_once()
    assert check.record_failed.call_args.kwargs["query_timestamps"] == [now]


# This test is AI-generated and has not been closely inspected by a human.
def test_dp_extrapolation_failure_uses_observation_query():
    now = datetime(2026, 10, 7, tzinfo=UTC)
    injected = InjectedFlight(
        uss_participant_id="sp",
        test_id="test-id",
        query_timestamp=now,
        query_duration_s=0,
        flight=injection.TestFlight(
            injection_id="injection-id",
            telemetry=[
                injection.RIDAircraftState(
                    timestamp=StringBasedDateTime(now),
                    position=injection.RIDAircraftPosition(lat=1, lng=1, alt=100),
                )
            ],
            details_responses=[],
        ),
    )
    observed_position = observation.Position(lat=1, lng=1, alt=100)
    # Constructors discard undeclared fields; explicitly add unexpected response data
    # to exercise the extrapolation failure reporting branch.
    observed_position["extrapolated"] = True
    observed = observation.Flight(
        id="observed-id", most_recent_position=observed_position
    )
    query = Query(
        request=RequestDescription(
            method="GET",
            url="https://observer.example/display_data",
            initiated_at=StringBasedDateTime(now),
        ),
        response=ResponseDescription(
            code=200, reported=StringBasedDateTime(now), elapsed_s=0
        ),
    )
    scenario = MagicMock(spec=UnitTestScenario)
    observer = MagicMock(participant_id="dp", base_url="https://observer.example")
    evaluator = RIDObservationEvaluator(
        config=EvaluationConfiguration(),
        test_scenario=scenario,
        rid_version=RIDVersion.f3411_22a,
        injected_flights=[injected],
    )
    evaluator._common_dictionary_evaluator = MagicMock()
    evaluator._retrieved_flight_details[observer.base_url] = {observed.id}

    evaluator._evaluate_normal_observation(
        observer, observation.GetDisplayDataResponse(flights=[observed]), query, {"sp"}
    )

    check = scenario.check.return_value.__enter__.return_value
    failure = next(
        call
        for call in check.record_failed.call_args_list
        if call.args
        and call.args[0]
        == "Position Data is using extrapolation when Telemetry is available."
    )
    assert str(now) in failure.kwargs["details"]
    assert "observation reported extrapolated telemetry" in failure.kwargs["details"]


def _assert_evaluate_sp_flight_recent_positions(
    f: Flight, query_time: datetime, outcome: bool
):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDObservationEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
            injected_flights=[],
        )
        evaluator._evaluate_sp_flight_recent_positions_times(
            f, query_time, RIDVersion.f3411_22a
        )

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_evaluate_sp_flight_recent_positions():
    some_time = datetime.now(UTC)
    # All samples within last minute: should pass
    _assert_evaluate_sp_flight_recent_positions(
        mock_flight(some_time, 7, 10), some_time, True
    )
    # oldest sample outside last minute: should fail
    _assert_evaluate_sp_flight_recent_positions(
        mock_flight(some_time, 8, 10), some_time, False
    )
    # No positions: not expected but this is not this test's problem
    _assert_evaluate_sp_flight_recent_positions(
        mock_flight(some_time, 0, 10), some_time, True
    )


def _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
    requested_area: s2sphere.LatLngRect, f: Flight, outcome: bool
):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDObservationEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
            injected_flights=[],
        )
        evaluator._evaluate_sp_flight_recent_positions_crossing_area_boundary(
            requested_area, f, RIDVersion.f3411_22a
        )

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_evaluate_sp_flight_recent_positions_crossing_area_boundary():
    # Mock flight with no recent position: should pass
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(0.5, 0.5),
        ),
        mock_flight(datetime.now(UTC), 0, 10),
        True,
    )
    # Mock flight with one recent position: should pass event if outside of area
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(0.5, 0.5),
        ),
        mock_flight(datetime.now(UTC), 1, 10),
        True,
    )

    # Mock flight with two recent positions within area: should pass
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2, 2),
        ),
        mock_flight(datetime.now(UTC), 2, 10),
        True,
    )

    # Mock flight with two recent positions outside area: should fail
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(0.5, 0.5),
        ),
        mock_flight(datetime.now(UTC), 2, 10),
        False,
    )

    # Mock flight with two recent positions, one of which is outside area: should pass
    f2_1 = mock_flight(datetime.now(UTC), 0, 0)
    f2_1.v22a_value.recent_positions = to_positions(
        [(1.0, 1.0), (-1.0, -1.0)], datetime.now(UTC)
    )
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2.0, 2.0),
        ),
        f2_1,
        True,
    )

    f2_2 = mock_flight(datetime.now(UTC), 0, 0)
    f2_2.v22a_value.recent_positions = to_positions(
        [(-1.0, -1.0), (1.0, 1.0)], datetime.now(UTC)
    )
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2.0, 2.0),
        ),
        f2_2,
        True,
    )

    # Mock flight with 3 recent positions completely outside requested area: should fail
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(0.5, 0.5),
        ),
        mock_flight(datetime.now(UTC), 3, 10),
        False,
    )

    # Mock flight with 3 recent positions, the second of which is in the area: should pass
    f3_1 = mock_flight(datetime.now(UTC), 0, 0)
    f3_1.v22a_value.recent_positions = to_positions(
        [(-1.0, -1.0), (1.0, 1.0), (3.0, 3.0)], datetime.now(UTC)
    )
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2.0, 2.0),
        ),
        f3_1,
        True,
    )

    # Mock flight with 3 recent positions, only the last of which is in the area: should fail
    f3_2 = mock_flight(datetime.now(UTC), 0, 0)
    f3_2.v22a_value.recent_positions = to_positions(
        [(-1.0, -1.0), (3.0, 3.0), (1.0, 1.0)], datetime.now(UTC)
    )
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2.0, 2.0),
        ),
        f3_2,
        False,
    )

    # Mock flight with 3 recent positions, only the first of which is in the area: should fail
    f3_3 = mock_flight(datetime.now(UTC), 0, 0)
    f3_3.v22a_value.recent_positions = to_positions(
        [(1.0, 1.0), (3.0, 3.0), (-1.0, -1.0)], datetime.now(UTC)
    )
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2.0, 2.0),
        ),
        f3_3,
        False,
    )

    # Mock flight with 3 recent positions within requested area: should pass
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2, 2),
        ),
        mock_flight(datetime.now(UTC), 3, 10),
        True,
    )

    # Mock flight with 4 recent positions, last position outside requested area: should pass
    f4_1 = mock_flight(datetime.now(UTC), 0, 0)
    f4_1.v22a_value.recent_positions = to_positions(
        [(1.0, 1.0), (1.0, 1.0), (1.0, 1.0), (3.0, 3.0)], datetime.now(UTC)
    )
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2.0, 2.0),
        ),
        f4_1,
        True,
    )

    # Mock flight with 4 recent positions, first position outside requested area: should pass
    f4_2 = mock_flight(datetime.now(UTC), 0, 0)
    f4_2.v22a_value.recent_positions = to_positions(
        [(3.0, 3.0), (1.0, 1.0), (1.0, 1.0), (1.0, 1.0)], datetime.now(UTC)
    )
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2.0, 2.0),
        ),
        f4_2,
        True,
    )

    # Mock flight completely within requested area: should pass
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2, 2),
        ),
        mock_flight(datetime.now(UTC), 7, 10),
        True,
    )

    # Mock flight completely outside requested area: should fail
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(0.5, 0.5),
        ),
        mock_flight(datetime.now(UTC), 7, 10),
        False,
    )
