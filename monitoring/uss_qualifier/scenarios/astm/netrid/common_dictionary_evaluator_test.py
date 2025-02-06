from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Any, Callable, TypeVar
from dataclasses import dataclass
from itertools import permutations

from implicitdict import StringBasedDateTime
from uas_standards.astm.f3411 import v22a
from uas_standards.astm.f3411.v22a.api import (
    Altitude,
    LatLngPoint,
    UAType,
)
from uas_standards.astm.f3411.v22a.constants import SpecialTrackDirection
from uas_standards.interuss.automated_testing.rid.v1 import injection
from uas_standards.interuss.automated_testing.rid.v1.observation import (
    OperatorAltitudeAltitudeType,
    RIDHeight,
)

from monitoring.monitorlib.fetch.rid import Flight
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.scenarios.astm.netrid.common_dictionary_evaluator import (
    RIDCommonDictionaryEvaluator,
)
from monitoring.uss_qualifier.scenarios.interuss.unit_test import UnitTestScenario


def _assert_operator_id(value_inj: str, value_obs: str, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )
        evaluator._evaluate_operator_id(value_inj, value_obs, [])

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_operator_id_non_ascii():
    _assert_operator_id("non_ascii©", "non_ascii©", False)


def test_operator_id_ascii():
    _assert_operator_id("ascii.1234", "ascii.1234", True)


def _assert_operator_location(
    position_inj,
    altitude_inj,
    altitude_type_inj,
    position,
    altitude,
    altitude_type,
    expected_passed_checks,
    expected_failed_checks,
):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )
        evaluator._evaluate_operator_location(
            position_inj,
            altitude_inj,
            altitude_type_inj,
            position,
            altitude,
            altitude_type,
            [],
        )

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
    valid_locations: List[
        Tuple[
            Optional[LatLngPoint],
            Optional[Altitude],
            Optional[OperatorAltitudeAltitudeType],
            Optional[LatLngPoint],
            Optional[Altitude],
            Optional[OperatorAltitudeAltitudeType],
            int,
        ]
    ] = [
        (
            LatLngPoint(lat=1.0, lng=1.0),
            None,
            None,
            LatLngPoint(lat=1.0, lng=1.0),
            None,
            None,
            2,
        ),
        (
            LatLngPoint(lat=-90.0, lng=180.0),
            None,
            None,
            LatLngPoint(lat=-90.0, lng=180.0),
            None,
            None,
            2,
        ),
        (
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(value=1),
            OperatorAltitudeAltitudeType("Takeoff"),
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(value=1),
            OperatorAltitudeAltitudeType("Takeoff"),
            6,
        ),
    ]
    for valid_location in valid_locations:
        _assert_operator_location(*valid_location, 0)

    invalid_locations: List[
        Tuple[
            Optional[LatLngPoint],
            Optional[Altitude],
            Optional[OperatorAltitudeAltitudeType],
            int,
            int,
        ]
    ] = [
        (
            LatLngPoint(lat=-90.001, lng=0),  # out of range and valid
            None,
            None,
            LatLngPoint(lat=-90.001, lng=0),  # out of range and valid
            None,
            None,
            1,
            1,
        ),
        (
            LatLngPoint(
                lat=0,  # valid
                lng=180.001,  # out of range
            ),
            None,
            None,
            LatLngPoint(
                lat=0,  # valid
                lng=180.001,  # out of range
            ),
            None,
            None,
            0,
            1,
        ),
        (
            LatLngPoint(lat=-90.001, lng=180.001),  # both out of range
            None,
            None,
            LatLngPoint(lat=-90.001, lng=180.001),  # both out of range
            None,
            None,
            0,
            2,
        ),
        (
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            None,
            None,
            LatLngPoint(
                lat="46°12'7.99 N",  # Float required
                lng="6°08'44.48 E",  # Float required
            ),
            None,
            None,
            0,
            2,
        ),
        (
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(value=1),
            "invalid",  # Invalid value
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(value=1),
            "invalid",  # Invalid value
            5,
            1,
        ),
        (
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(
                value=1000.9,
                units="FT",  # Invalid value
                reference="UNKNOWN",  # Invalid value
            ),
            "Takeoff",
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(
                value=1000.9,
                units="FT",  # Invalid value
                reference="UNKNOWN",  # Invalid value
            ),
            "Takeoff",
            5,
            2,
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

        evaluator._evaluate_operational_status(value, [])

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_operational_status():
    _assert_operational_status("Undeclared", True)  # v19 and v22a
    _assert_operational_status("Emergency", True)  # v22a only
    _assert_operational_status("Invalid", False)  # Invalid


def _assert_timestamp(value_inj: str, value_obs: str, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        evaluator._evaluate_timestamp(
            StringBasedDateTime(value_inj), StringBasedDateTime(value_obs), []
        )

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_timestamp():
    _assert_timestamp("2023-09-13T04:43:00.1Z", "2023-09-13T04:43:00.1Z", True)  # Ok
    _assert_timestamp("2023-09-13T04:43:00Z", "2023-09-13T04:43:00Z", True)  # Ok
    _assert_timestamp(
        "2023-09-13T04:43:00.501Z", "2023-09-13T04:43:00.501Z", True
    )  # Ok
    _assert_timestamp(
        "2023-09-13T04:43:00.1+07:00", "2023-09-13T04:43:00.1+07:00", False
    )  # Wrong timezone


def _assert_speed(value_inj: float, value_obs: float, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        evaluator._evaluate_speed(value_inj, value_obs, [])

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_speed():
    _assert_speed(1, 1, True)  # Ok
    _assert_speed(20.75, 20.75, True)  # Ok
    _assert_speed(400, 400, False)  # Fail, above MaxSpeed
    _assert_speed(23.3, 23.3, True)  # Ok
    _assert_speed(23.13, 23.25, True)  # Ok
    _assert_speed(23.12, 23.0, True)  # Ok
    _assert_speed(23.13, 23.0, False)  # Ok
    _assert_speed(23.13, 23.5, False)  # Ok


def _assert_track(value_inj: float, value_obs: float, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        evaluator._evaluate_track(value_inj, value_obs, [])

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_track():
    _assert_track(1, 1, True)  # Ok
    _assert_track(-359, -359, True)  # Ok
    _assert_track(359.5, 0, True)  # Ok
    _assert_track(359.9, 0, True)  # Ok
    _assert_track(359.4, 0, False)  # Rounded the wrong way
    _assert_track(359.4, 359.0, True)  # Ok
    _assert_track(400, 400, False)  # Fail, above MaxTrackDirection
    _assert_track(-360, -360, False)  # Fail, below MinTrackDirection
    _assert_track(23.3, 23.3, True)  # Wrong resolution
    _assert_track(SpecialTrackDirection, SpecialTrackDirection, True)


def _assert_height(value_inj: injection.RIDHeight, value_obs: RIDHeight, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        evaluator._evaluate_height(value_inj, value_obs, [])

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_height():
    _assert_height(None, None, True)  # Ok
    _assert_height(
        injection.RIDHeight(distance=10, reference="TakeoffLocation"),
        RIDHeight(distance=10, reference="TakeoffLocation"),
        True,
    )  # Ok
    _assert_height(
        injection.RIDHeight(distance=10.101, reference="TakeoffLocation"),
        RIDHeight(distance=10.101, reference="TakeoffLocation"),
        True,
    )  # Ok
    _assert_height(
        injection.RIDHeight(distance=10.101, reference="TakeoffLocation"),
        RIDHeight(distance=10.101, reference="Moon"),
        False,
    )  # Wrong reference
    _assert_height(
        injection.RIDHeight(distance=10.0, reference="TakeoffLocation"),
        RIDHeight(distance=11.1, reference="TakeoffLocation"),
        False,
    )  # Too far apart
    _assert_height(
        injection.RIDHeight(distance=10.0, reference="GroundLevel"),
        RIDHeight(distance=11.1, reference="TakeoffLocation"),
        False,
    )  # mismatching reference


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


@dataclass
class GenericEvaluatorTestCase:
    test_name: str
    injected_value: str
    sp_value: str
    dp_value: str = None
    ignore_dp_test: bool = False


def _assert_generic_evaluator(testcase: GenericEvaluatorTestCase, outcome: bool):
    def value_validator(v: str) -> str:
        if v == "invalid":
            raise ValueError
        return v

    def value_comparator(v1: str, v2: str) -> bool:
        return v1 == v2

    dummy_injected = {"test": testcase.injected_value}
    dummy_sp = {"test": testcase.sp_value}
    dummy_dp = {"test": testcase.dp_value}

    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        # SP Check
        evaluator._generic_evaluator(
            injected_field_name="test",
            sp_field_name="test",
            dp_field_name="test",
            field_human_name="test",
            value_validator=value_validator,
            observed_value_validator=None,
            injection_required_field=False,
            unknown_value="default",
            value_comparator=value_comparator,
            injected=dummy_injected,
            sp_observed=dummy_sp,
            dp_observed=None,
            participant=0,
            query_timestamp=datetime.now(),
        )

        if not testcase.ignore_dp_test:

            # DP Check
            evaluator._generic_evaluator(
                injected_field_name="test",
                sp_field_name="test",
                dp_field_name="test",
                field_human_name="test",
                value_validator=value_validator,
                observed_value_validator=None,
                injection_required_field=False,
                unknown_value="default",
                value_comparator=value_comparator,
                injected=dummy_injected,
                sp_observed=None,
                dp_observed=dummy_dp,
                participant=0,
                query_timestamp=datetime.now(),
            )

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()

    assert unit_test_scenario.get_report().successful == outcome

    if not outcome:

        found_correct_reason = False

        for c in unit_test_scenario.get_report().cases:
            for step in c.steps:
                for failed_check in step.failed_checks:
                    if (
                        failed_check.additional_data[
                            "RIDCommonDictionaryEvaluatorCheckID"
                        ]
                        == testcase.test_name
                    ):
                        found_correct_reason = True

        assert found_correct_reason, testcase


def test_generic_evaluator():
    """Test various generic evaluator cases"""

    failling_tests = [
        GenericEvaluatorTestCase(
            test_name="C3",
            injected_value="valid",
            sp_value=None,
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C5",
            injected_value="valid",
            sp_value="invalid",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C6",
            injected_value=None,
            sp_value="something-else",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C6",
            injected_value=None,
            sp_value=None,
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C6",
            injected_value=None,
            sp_value="valid",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C6",
            injected_value=None,
            sp_value="invalid",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C7",
            injected_value="valid",
            sp_value="valid2",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C9",
            injected_value="valid",
            sp_value="valid",
            dp_value="invalid",
        ),
        GenericEvaluatorTestCase(
            test_name="C10",
            injected_value="valid",
            sp_value="valid",
            dp_value="valid2",
        ),
    ]

    success_tests = [
        GenericEvaluatorTestCase(
            test_name="C6 (But ok)",
            injected_value=None,
            sp_value="default",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C8",
            injected_value="valid",
            sp_value="valid",
            dp_value=None,
        ),
        GenericEvaluatorTestCase(
            test_name="C8",
            injected_value="valid2",
            sp_value="valid2",
            dp_value=None,
        ),
        GenericEvaluatorTestCase(
            test_name="General",
            injected_value="valid",
            sp_value="valid",
            dp_value="valid",
        ),
        GenericEvaluatorTestCase(
            test_name="General",
            injected_value="valid2",
            sp_value="valid2",
            dp_value="valid2",
        ),
    ]

    for test in failling_tests:
        _assert_generic_evaluator(test, False)
    for test in success_tests:
        _assert_generic_evaluator(test, True)


T = TypeVar("T")


def _assert_generic_evaluator_call(
    fct: str,
    injected: Any,
    sp_observed: Any,
    dp_observed: Any,
    outcome: bool,
    rid_version: Optional[RIDVersion] = RIDVersion.f3411_22a,
    wanted_fail: Optional[list[str]] = None,
):
    """
    Verify that the 'fct' function on the RIDCommonDictionaryEvaluator is returning the expected result.

    Args:
        fct: name of the function to test
        injected: injected data
        sp_observed: flight observed through the SP API.
        dp_observed: flight observed through the observation API.
        outcome: Expected outcome of the test
        rid_version: RIDVersion to use, default to 22a
        wanted_fail: A list of specific C-code that should fail. If not set, not tested.
    """

    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=rid_version,
        )

        # SP Check
        getattr(evaluator, fct)(
            injected=injected,
            sp_observed=sp_observed,
            dp_observed=None,
            participant=0,
            query_timestamp=datetime.now(),
        )

        # DP Check
        getattr(evaluator, fct)(
            injected=injected,
            sp_observed=None,
            dp_observed=dp_observed,
            participant=0,
            query_timestamp=datetime.now(),
        )

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()

    assert unit_test_scenario.get_report().successful == outcome

    if wanted_fail:

        found_correct_reason = False

        for c in unit_test_scenario.get_report().cases:
            for step in c.steps:
                for failed_check in step.failed_checks:
                    if (
                        failed_check.additional_data[
                            "RIDCommonDictionaryEvaluatorCheckID"
                        ]
                        in wanted_fail
                    ):
                        found_correct_reason = True

        assert found_correct_reason


def _assert_generic_evaluator_result(
    fct: str,
    *setters_and_values: list[Any],
    outcome: bool,
    wanted_fail: Optional[list[str]] = None,
    rid_version: Optional[RIDVersion] = None
):
    """
    Helper to call _assert_generic_evaluator_call that build mocked objects first and do the call.

    Args:
        fct: name of the function to test
        injected_field_setter: See _build_generic_evaluator_objects's doc
        sp_field_setter: See _build_generic_evaluator_objects's doc
        dp_field_setter: See _build_generic_evaluator_objects's doc
        injected_value: See _build_generic_evaluator_objects's doc
        sp_value: See _build_generic_evaluator_objects's doc
        dp_value: See _build_generic_evaluator_objects's doc
        outcome: See _assert_generic_evaluator_call's doc
        wanted_fail: See _assert_generic_evaluator_call's doc
        rid_version: See _assert_generic_evaluator_call's doc
    """

    mocks = _build_generic_evaluator_objects(*setters_and_values)
    _assert_generic_evaluator_call(
        fct, *mocks, outcome=outcome, wanted_fail=wanted_fail, rid_version=rid_version
    )


def _build_generic_evaluator_objects(
    injected_field_setter: Callable[[Any, T], list[Any]],
    sp_field_setter: Callable[[Any, T], Any],
    dp_field_setter: Callable[[Any, T], Any],
    injected_value: T,
    sp_value: T,
    dp_value: T,
):
    """
    Helper to build mock objects passed to _assert_generic_evaluator_call, using mock functions and values.

    Args:
        injected_field_setter: Function taking a mocked injected object and the injected_value, who needs to return return the object with the value set
        sp_field_setter: Function taking a mocked sp_observed object and the sp_value, who needs to return the object with the value set
        dp_field_setter: Function taking a mocked dp_observed object and the dp_value, who needs to return the object with the value set
        injected_value: The value that should be insered into the mock objects as injected
        sp_value: The value that should be insered into the mock objects as the sp value
        dp_value: The value that should be insered into the mock objects as the dp value
    """

    injected = injected_field_setter({}, injected_value)
    sp_observed = sp_field_setter({}, sp_value)
    dp_observed = dp_field_setter({}, dp_value)

    return injected, sp_observed, dp_observed


def _assert_generic_evaluator_correct_field_is_used(
    *fct_and_setters: list[Any], valid_value: T, valid_value_2: T
):
    """
    Test that a _evaluate function is comparing the correct fields by doing some basic calls.

    Args:
        fct: name of the function to test
        injected_field_setter: See _build_generic_evaluator_objects's doc
        sp_field_setter: See _build_generic_evaluator_objects's doc
        dp_field_setter: See _build_generic_evaluator_objects's doc
        injected_value: See _build_generic_evaluator_objects's doc
        sp_value: See _build_generic_evaluator_objects's doc
        dp_value: See _build_generic_evaluator_objects's doc
        valid_value: A usable value that should be valid in every case (injected/sp/dp).
        valid_value_2: Another usable value that should be valid in every case (injected/sp/dp), different from valid_value.
    """

    _assert_generic_evaluator_result(
        *fct_and_setters, valid_value, valid_value, valid_value, outcome=True
    )
    _assert_generic_evaluator_result(
        *fct_and_setters, valid_value_2, valid_value, valid_value, outcome=False
    )
    _assert_generic_evaluator_result(
        *fct_and_setters, valid_value, valid_value_2, valid_value, outcome=False
    )
    _assert_generic_evaluator_result(
        *fct_and_setters, valid_value, valid_value, valid_value_2, outcome=False
    )


def _assert_generic_evaluator_valid_value(
    *fct_and_setters: list[Any],
    valid_value: T,
    rid_version: Optional[RIDVersion] = None
):
    """
    Test that a _evaluate function is handeling a specifc value as valid.

    Args:
        fct: name of the function to test
        injected_field_setter: See _build_generic_evaluator_objects's doc
        sp_field_setter: See _build_generic_evaluator_objects's doc
        dp_field_setter: See _build_generic_evaluator_objects's doc
        injected_value: See _build_generic_evaluator_objects's doc
        sp_value: See _build_generic_evaluator_objects's doc
        dp_value: See _build_generic_evaluator_objects's doc
        valid_value: A usable value that should be valid in every case (injected/sp/dp).
        rid_version: Optional rid version to perform the test.
    """

    _assert_generic_evaluator_result(
        *fct_and_setters,
        valid_value,
        valid_value,
        valid_value,
        outcome=True,
        rid_version=rid_version,
    )


def _assert_generic_evaluator_invalid_value(
    *fct_and_setters: list[Any],
    invalid_value: T,
    valid_value: T,
    rid_version: Optional[RIDVersion] = None
):
    """
    Test that a _evaluate function is handeling a specifc value as invalid.

    Args:
        fct: name of the function to test
        injected_field_setter: See _build_generic_evaluator_objects's doc
        sp_field_setter: See _build_generic_evaluator_objects's doc
        dp_field_setter: See _build_generic_evaluator_objects's doc
        injected_value: See _build_generic_evaluator_objects's doc
        sp_value: See _build_generic_evaluator_objects's doc
        dp_value: See _build_generic_evaluator_objects's doc
        invalid_value: A non-valid value that shouldn't be accepeted in all cases (injected/sp/dp)
        valid_value: A usable value that should be valid in every case (injected/sp/dp).
        rid_version: Optional rid version to perform the test.
    """
    try:
        _assert_generic_evaluator_result(
            *fct_and_setters,
            invalid_value,
            valid_value,
            valid_value,
            outcome=False,
            rid_version=rid_version,
        )
        raised = False
    except Exception:
        raised = True

    assert raised, "Exception should have been raised"

    _assert_generic_evaluator_result(
        *fct_and_setters,
        valid_value,
        invalid_value,
        invalid_value,
        outcome=False,
        rid_version=rid_version,
        wanted_fail=["C5", "C9"],
    )


def _assert_generic_evaluator_invalid_observed_value(
    *fct_and_setters: list[Any],
    invalid_value: T,
    rid_version: Optional[RIDVersion] = None
):
    """
    Test that a _evaluate function is handeling a specifc value as invalid when observed.

    Args:
        fct: name of the function to test
        injected_field_setter: See _build_generic_evaluator_objects's doc
        sp_field_setter: See _build_generic_evaluator_objects's doc
        dp_field_setter: See _build_generic_evaluator_objects's doc
        injected_value: See _build_generic_evaluator_objects's doc
        sp_value: See _build_generic_evaluator_objects's doc
        dp_value: See _build_generic_evaluator_objects's doc
        invalid_value: A valid value that shouldn't be accepeted in observable cases (sp/dp).
        rid_version: Optional rid version to perform the test.
    """
    _assert_generic_evaluator_result(
        *fct_and_setters,
        invalid_value,
        invalid_value,
        invalid_value,
        outcome=False,
        rid_version=rid_version,
    )


def _assert_generic_evaluator_defaults(
    *fct_and_setters: list[Any], default_value: T, valid_value: T
):
    """
    Test that a _evaluate function is using a specifc value as the default value.

    Args:
        fct: name of the function to test
        injected_field_setter: See _build_generic_evaluator_objects's doc
        sp_field_setter: See _build_generic_evaluator_objects's doc
        dp_field_setter: See _build_generic_evaluator_objects's doc
        injected_value: See _build_generic_evaluator_objects's doc
        sp_value: See _build_generic_evaluator_objects's doc
        dp_value: See _build_generic_evaluator_objects's doc
        default: A valid value that should be used as default value when no value is injected.
        valid_value: A usable value that should be valid in every case (injected/sp/dp), different from the default value.
    """
    _assert_generic_evaluator_result(
        *fct_and_setters,
        None,
        valid_value,
        valid_value,
        outcome=False,
        wanted_fail=["C6", "C10"],
    )
    _assert_generic_evaluator_result(
        *fct_and_setters, None, default_value, default_value, outcome=True
    )


def _assert_generic_evaluator_dont_have_default(
    *fct_and_setters: list[Any], valid_value: T, valid_value_2: T
):
    """
    Test that a _evaluate function isn't providing a default value.

    Args:
        fct: name of the function to test
        injected_field_setter: See _build_generic_evaluator_objects's doc
        sp_field_setter: See _build_generic_evaluator_objects's doc
        dp_field_setter: See _build_generic_evaluator_objects's doc
        injected_value: See _build_generic_evaluator_objects's doc
        sp_value: See _build_generic_evaluator_objects's doc
        dp_value: See _build_generic_evaluator_objects's doc
        valid_value: A usable value that should be valid in every case (injected/sp/dp).
        valid_value_2: Another usable value that should be valid in every case (injected/sp/dp), different from valid_value.
    """

    # The test should fail, because the generic evaluator disallow empty
    # mandatory value for the programmer
    got_exception = False

    try:
        _assert_generic_evaluator_result(
            *fct_and_setters, None, valid_value, valid_value, outcome=False
        )
    except:
        got_exception = True

    assert got_exception

    # We test with two valid values that we get a fail from C3 (missing value)
    # and C7 (value not equal), to ensure the function is not providing a
    # default valid value (that could, by chance, be equal to valid_value,
    # hence the two valid values)
    _assert_generic_evaluator_result(
        *fct_and_setters,
        valid_value,
        None,
        None,
        outcome=False,
        wanted_fail=["C3", "C7"],
    )

    _assert_generic_evaluator_result(
        *fct_and_setters,
        valid_value_2,
        None,
        None,
        outcome=False,
        wanted_fail=["C3", "C7"],
    )


def _assert_generic_evaluator_equivalent(
    *fct_and_setters: list[Any], v1: T, v2: T, rid_version: Optional[RIDVersion] = None
):
    """
    Test that a _evaluate function is considering two value as equivalent.

    Args:
        fct: name of the function to test
        injected_field_setter: See _build_generic_evaluator_objects's doc
        sp_field_setter: See _build_generic_evaluator_objects's doc
        dp_field_setter: See _build_generic_evaluator_objects's doc
        injected_value: See _build_generic_evaluator_objects's doc
        sp_value: See _build_generic_evaluator_objects's doc
        dp_value: See _build_generic_evaluator_objects's doc
        v1: A valid value that should be considered equal to v2.
        v2: A valid value that should be considered equal to v1.
        rid_version: Optional rid version to perform the test.
    """
    _assert_generic_evaluator_result(
        *fct_and_setters, v1, v2, v2, outcome=True, rid_version=rid_version
    )


def _assert_generic_evaluator_not_equivalent(
    *fct_and_setters: list[Any], v1: T, v2: T, rid_version: Optional[RIDVersion] = None
):
    """
    Test that a _evaluate function is considering two value as not equivalent.

    Args:
        fct: name of the function to test
        injected_field_setter: See _build_generic_evaluator_objects's doc
        sp_field_setter: See _build_generic_evaluator_objects's doc
        dp_field_setter: See _build_generic_evaluator_objects's doc
        injected_value: See _build_generic_evaluator_objects's doc
        sp_value: See _build_generic_evaluator_objects's doc
        dp_value: See _build_generic_evaluator_objects's doc
        v1: A valid value that shouldn't be considered equal to v2.
        v2: A valid value that shouldn't be considered equal to v1.
        rid_version: Optional rid version to perform the test.
    """
    _assert_generic_evaluator_result(
        *fct_and_setters, v1, v2, v2, outcome=False, rid_version=rid_version
    )


def test_evaluate_ua_type():
    """Test the evaluate_ua_type function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["aircraft_type"] = value
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["aircraft_type"] = value
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["aircraft_type"] = value
        return flight

    base_args = (
        "_evaluate_ua_type",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=injection.UAType.Helicopter,
        valid_value_2=injection.UAType.Glider,
    )

    for valid_value in [
        "NotDeclared",
        "Aeroplane",
        "Helicopter",
        "Gyroplane",
        "Ornithopter",
        "Glider",
        "Kite",
        "FreeBalloon",
        "CaptiveBalloon",
        "Airship",
        "FreeFallOrParachute",
        "Rocket",
        "TetheredPoweredAircraft",
        "GroundObstacle",
        "Other",
    ]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in ["Spaceship", "FlyingBroom"]:
        _assert_generic_evaluator_invalid_value(
            *base_args,
            invalid_value=invalid_value,
            valid_value=injection.UAType.Helicopter,
        )

    # HybridLift and VTOl are version specific
    _assert_generic_evaluator_valid_value(
        *base_args, valid_value="HybridLift", rid_version=RIDVersion.f3411_22a
    )
    _assert_generic_evaluator_valid_value(
        *base_args, valid_value="VTOL", rid_version=RIDVersion.f3411_19
    )

    _assert_generic_evaluator_invalid_observed_value(
        *base_args, invalid_value="HybridLift", rid_version=RIDVersion.f3411_19
    )
    _assert_generic_evaluator_invalid_observed_value(
        *base_args, invalid_value="VTOL", rid_version=RIDVersion.f3411_22a
    )

    _assert_generic_evaluator_defaults(
        *base_args,
        default_value=injection.UAType.NotDeclared,
        valid_value=injection.UAType.Helicopter,
    )

    for v1, v2 in permutations(
        [
            "NotDeclared",
            "Aeroplane",
            "Helicopter",
            "Gyroplane",
            "Ornithopter",
            "Glider",
            "Kite",
            "FreeBalloon",
            "CaptiveBalloon",
            "Airship",
            "FreeFallOrParachute",
            "Rocket",
            "TetheredPoweredAircraft",
            "GroundObstacle",
            "Other",
            "HybridLift",
            "VTOL",
        ],
        2,
    ):
        rid_version = (
            RIDVersion.f3411_19 if v2 == "VTOL" else RIDVersion.f3411_22a
        )  # VTOL is only valid as observed value in v19

        if v1 in ["VTOL", "HybridLift"] and v2 in ["VTOL", "HybridLift"]:
            _assert_generic_evaluator_equivalent(
                *base_args, v1=v1, v2=v2, rid_version=rid_version
            )
        else:
            _assert_generic_evaluator_not_equivalent(
                *base_args, v1=v1, v2=v2, rid_version=rid_version
            )


def test_evaluate_timestamp_accuracy():
    """Test the evaluate_timestamp_accuracy function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["timestamp_accuracy"] = value
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"current_state": {"timestamp_accuracy": value}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["current_state"] = {"timestamp_accuracy": value}
        return flight

    base_args = (
        "_evaluate_timestamp_accuracy",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=42,
        valid_value_2=3.14,
    )

    # Value should be >= 0
    for valid_value in [0, 0.01, 42, 3.14, 10000]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in [-1, -0.01, -0.05, -10000]:
        _assert_generic_evaluator_invalid_value(
            *base_args, invalid_value=invalid_value, valid_value=42
        )

    _assert_generic_evaluator_dont_have_default(
        *base_args,
        valid_value=42,
        valid_value_2=3.14,
    )

    # Resolution is in steps of 0.05
    for v1 in [0, 0.01, 42, 3.14, 10000]:
        for valid_delta in [
            0,
            0.01,
            0.02,
            0.03,
            0.04,
            0.045,
            0.049,
            -0.01,
            -0.02,
            -0.03,
            -0.04,
            -0.045,
            -0.049,
        ]:
            v2 = v1 + valid_delta

            if v2 > 0:  # Ensure value stays valid
                _assert_generic_evaluator_equivalent(*base_args, v1=v1, v2=v2)
        for invalid_delta in [
            0.051,
            1,
            42,
            -0.051,
            -1,
            -42,
        ]:  # Float values are funny, we cannot test 0.05 because check may 'round' that to 0.04999999999999716
            v2 = v1 + invalid_delta

            if v2 > 0:  # Ensure value stays valid
                _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)
