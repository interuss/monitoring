from datetime import datetime, timedelta, timezone
import s2sphere
from typing import List, Tuple
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.fetch.rid import Flight
from monitoring.uss_qualifier.scenarios.astm.netrid.common_dictionary_evaluator import (
    RIDCommonDictionaryEvaluator,
)
from monitoring.uss_qualifier.scenarios.interuss.unit_test import UnitTestScenario
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from uas_standards.astm.f3411.v22a.api import (
    Altitude,
    LatLngPoint,
    OperatorLocation,
    UAType,
)
from uas_standards.astm.f3411 import v22a


def _assert_operator_id(value: str, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )
        evaluator.evaluate_operator_id(value, RIDVersion.f3411_22a)

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_operator_id_non_ascii():
    _assert_operator_id("non_ascii©", False)


def test_operator_id_ascii():
    _assert_operator_id("ascii.1234", True)


def _assert_operator_location(
    value: OperatorLocation, expected_passed_checks, expected_failed_checks
):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )
        evaluator.evaluate_operator_location(value, RIDVersion.f3411_22a)

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert (
        len(list(unit_test_scenario.get_report().query_passed_checks()))
        == expected_passed_checks
    )
    assert (
        len(list(unit_test_scenario.get_report().query_failed_checks()))
        == expected_failed_checks
    )


def test_operator_location():
    valid_locations: List[Tuple[OperatorLocation, int]] = [
        (
            OperatorLocation(
                position=LatLngPoint(lat=1.0, lng=1.0),
            ),
            1,
        ),
        (
            OperatorLocation(
                position=LatLngPoint(lat=-90.0, lng=180.0),
            ),
            1,
        ),
        (
            OperatorLocation(
                position=LatLngPoint(
                    lat=46.2,
                    lng=6.1,
                ),
                altitude=Altitude(value=1),
                altitude_type="Takeoff",
            ),
            3,
        ),
    ]
    for valid_location in valid_locations:
        _assert_operator_location(*valid_location, 0)

    invalid_locations: List[Tuple[OperatorLocation, int, int]] = [
        (
            OperatorLocation(
                position=LatLngPoint(lat=-90.001, lng=0),  # out of range and valid
            ),
            0,
            1,
        ),
        (
            OperatorLocation(
                position=LatLngPoint(
                    lat=0,  # valid
                    lng=180.001,  # out of range
                ),
            ),
            0,
            1,
        ),
        (
            OperatorLocation(
                position=LatLngPoint(lat=-90.001, lng=180.001),  # both out of range
            ),
            0,
            2,
        ),
        (
            OperatorLocation(
                position=LatLngPoint(
                    lat="46°12'7.99 N",  # Float required
                    lng="6°08'44.48 E",  # Float required
                ),
            ),
            0,
            2,
        ),
        (
            OperatorLocation(
                position=LatLngPoint(
                    lat=46.2,
                    lng=6.1,
                ),
                altitude=Altitude(value=1),
                altitude_type="invalid",  # Invalid value
            ),
            2,
            1,
        ),
        (
            OperatorLocation(
                position=LatLngPoint(
                    lat=46.2,
                    lng=6.1,
                ),
                altitude=Altitude(value=1000.9),  # Invalid value
                altitude_type="Takeoff",
            ),
            2,
            1,
        ),
        (
            OperatorLocation(
                position=LatLngPoint(
                    lat=46.2,
                    lng=6.1,
                ),
                altitude=Altitude(
                    value=1000.9,  # Invalid value
                    units="FT",  # Invalid value
                    reference="UNKNOWN",  # Invalid value
                ),
                altitude_type="Takeoff",
            ),
            2,
            3,
        ),
    ]
    for invalid_location in invalid_locations:
        _assert_operator_location(*invalid_location)


def _assert_operational_status(value: str, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        evaluator.evaluate_operational_status(value, RIDVersion.f3411_22a)

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_operational_status():
    _assert_operational_status("Undeclared", True)  # v19 and v22a
    _assert_operational_status("Emergency", True)  # v22a only
    _assert_operational_status("Invalid", False)  # Invalid


def _assert_evaluate_sp_flight_recent_positions(
    f: Flight, query_time: datetime, outcome: bool
):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )
        evaluator.evaluate_sp_flight_recent_positions_times(
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
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )
        evaluator.evaluate_sp_flight_recent_positions_crossing_area_boundary(
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


def mock_flight(
    last_position_time: datetime,
    positions_count: int,
    positions_time_delta_s: int,
    position: Tuple[int, int] = (1.0, 1.0),
) -> Flight:
    v22a_flight = v22a.api.RIDFlight(
        id="flightId",
        aircraft_type=UAType.Aeroplane,
        current_state=None,  # Not required for tests at the moment
        operating_area=None,  # Not required for tests at the moment
        simulated=True,
        recent_positions=mock_positions(
            last_position_time, positions_count, positions_time_delta_s, position
        ),
    )
    return Flight(v22a_value=v22a_flight)


def mock_positions(
    last_time: datetime,
    amount: int,
    positions_time_delta_s: int,
    position: Tuple[int, int] = (1.0, 1.0),
) -> List[v22a.api.RIDRecentAircraftPosition]:
    """generate a list of positions with the last one at last_time and the next ones going back in time by 10 seconds"""
    return [
        v22a.api.RIDRecentAircraftPosition(
            time=v22a.api.Time(
                value=v22a.api.StringBasedDateTime(
                    last_time - timedelta(seconds=positions_time_delta_s * i)
                )
            ),
            position=v22a.api.RIDAircraftPosition(lat=position[0], lng=position[1]),
        )
        for i in range(amount)
    ]


def to_positions(
    coords: List[Tuple[float, float]],
    first_time: datetime,
    positions_time_delta_s: int = 1,
) -> v22a.api.RIDRecentAircraftPosition:
    """transform the collection of coordinates"""
    return [
        v22a.api.RIDRecentAircraftPosition(
            time=v22a.api.Time(
                value=v22a.api.StringBasedDateTime(
                    first_time - timedelta(seconds=positions_time_delta_s * i)
                )
            ),
            position=v22a.api.RIDAircraftPosition(lat=coords[i][0], lng=coords[i][1]),
        )
        for i in range(len(coords))
    ]
