from datetime import datetime, timezone

import s2sphere

from monitoring.monitorlib.fetch.rid import Flight
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.scenarios.astm.netrid.common_dictionary_evaluator_test import (
    mock_flight,
    to_positions,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.display_data_evaluator import (
    RIDObservationEvaluator,
)
from monitoring.uss_qualifier.scenarios.interuss.unit_test import UnitTestScenario


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

    some_time = datetime.now(timezone.utc)
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
        mock_flight(datetime.now(timezone.utc), 0, 10),
        True,
    )
    # Mock flight with one recent position: should pass event if outside of area
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(0.5, 0.5),
        ),
        mock_flight(datetime.now(timezone.utc), 1, 10),
        True,
    )

    # Mock flight with two recent positions within area: should pass
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2, 2),
        ),
        mock_flight(datetime.now(timezone.utc), 2, 10),
        True,
    )

    # Mock flight with two recent positions outside area: should fail
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(0.5, 0.5),
        ),
        mock_flight(datetime.now(timezone.utc), 2, 10),
        False,
    )

    # Mock flight with two recent positions, one of which is outside area: should pass
    f2_1 = mock_flight(datetime.now(timezone.utc), 0, 0)
    f2_1.v22a_value.recent_positions = to_positions(
        [(1.0, 1.0), (-1.0, -1.0)], datetime.now(timezone.utc)
    )
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(2.0, 2.0),
        ),
        f2_1,
        True,
    )

    f2_2 = mock_flight(datetime.now(timezone.utc), 0, 0)
    f2_2.v22a_value.recent_positions = to_positions(
        [(-1.0, -1.0), (1.0, 1.0)], datetime.now(timezone.utc)
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
        mock_flight(datetime.now(timezone.utc), 3, 10),
        False,
    )

    # Mock flight with 3 recent positions, the second of which is in the area: should pass
    f3_1 = mock_flight(datetime.now(timezone.utc), 0, 0)
    f3_1.v22a_value.recent_positions = to_positions(
        [(-1.0, -1.0), (1.0, 1.0), (3.0, 3.0)], datetime.now(timezone.utc)
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
    f3_2 = mock_flight(datetime.now(timezone.utc), 0, 0)
    f3_2.v22a_value.recent_positions = to_positions(
        [(-1.0, -1.0), (3.0, 3.0), (1.0, 1.0)], datetime.now(timezone.utc)
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
    f3_3 = mock_flight(datetime.now(timezone.utc), 0, 0)
    f3_3.v22a_value.recent_positions = to_positions(
        [(1.0, 1.0), (3.0, 3.0), (-1.0, -1.0)], datetime.now(timezone.utc)
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
        mock_flight(datetime.now(timezone.utc), 3, 10),
        True,
    )

    # Mock flight with 4 recent positions, last position outside requested area: should pass
    f4_1 = mock_flight(datetime.now(timezone.utc), 0, 0)
    f4_1.v22a_value.recent_positions = to_positions(
        [(1.0, 1.0), (1.0, 1.0), (1.0, 1.0), (3.0, 3.0)], datetime.now(timezone.utc)
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
    f4_2 = mock_flight(datetime.now(timezone.utc), 0, 0)
    f4_2.v22a_value.recent_positions = to_positions(
        [(3.0, 3.0), (1.0, 1.0), (1.0, 1.0), (1.0, 1.0)], datetime.now(timezone.utc)
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
        mock_flight(datetime.now(timezone.utc), 7, 10),
        True,
    )

    # Mock flight completely outside requested area: should fail
    _assert_evaluate_sp_flight_recent_positions_crossing_area_boundary(
        s2sphere.LatLngRect(
            s2sphere.LatLng.from_degrees(0.0, 0.0),
            s2sphere.LatLng.from_degrees(0.5, 0.5),
        ),
        mock_flight(datetime.now(timezone.utc), 7, 10),
        False,
    )
