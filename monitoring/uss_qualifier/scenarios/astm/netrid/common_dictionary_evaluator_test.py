import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import permutations
from typing import Any, Callable, List, Optional, Tuple, TypeVar

from implicitdict import ImplicitDict
from uas_standards.ansi_cta_2063_a import SerialNumber
from uas_standards.astm.f3411 import v22a
from uas_standards.astm.f3411.v22a.api import (
    UASID,
    Altitude,
    HorizontalAccuracy,
    LatLngPoint,
    RIDHeightReference,
    RIDOperationalStatus,
    SpeedAccuracy,
    UAType,
    VerticalAccuracy,
)
from uas_standards.interuss.automated_testing.rid.v1 import injection
from uas_standards.interuss.automated_testing.rid.v1.observation import (
    OperatorAltitudeAltitudeType,
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
            test_name="C5",
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
T2 = TypeVar("T2")


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

    if rid_version is None:
        rid_version = RIDVersion.f3411_22a

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
    *fct_and_setters: list[Any], default_value: T2, valid_value: T
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

    # Resolution is in steps of 0.1
    for v1 in [0, 0.01, 42, 3.14, 10000]:
        for valid_delta in [
            0,
            0.01,
            0.02,
            0.03,
            0.04,
            0.045,
            0.099,
            -0.01,
            -0.02,
            -0.03,
            -0.04,
            -0.045,
            -0.099,
        ]:
            v2 = v1 + valid_delta

            if v2 > 0:  # Ensure value stays valid
                _assert_generic_evaluator_equivalent(*base_args, v1=v1, v2=v2)
        for invalid_delta in [
            0.11,
            1,
            42,
            -0.11,
            -1,
            -42,
        ]:  # Float values are funny, we cannot test 0.05 because check may 'round' that to 0.04999999999999716
            v2 = v1 + invalid_delta

            if v2 > 0:  # Ensure value stays valid
                _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)


def test_evaluate_speed():
    """Test the evaluate_speed function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["speed"] = value
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"current_state": {"speed": value}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["current_state"] = {"speed": value}
        return flight

    base_args = (
        "_evaluate_speed",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=42,
        valid_value_2=3.14,
    )

    # Value should be between -254.25, 254.25 or the special 255 value
    for valid_value in [0, 0.01, 42, 3.14, 254.25, 255]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in [-255, 254.5, -254.5, -1000, 1000, -0.01, -42, -3.14, -254.25]:
        _assert_generic_evaluator_invalid_value(
            *base_args, invalid_value=invalid_value, valid_value=42
        )

    _assert_generic_evaluator_dont_have_default(
        *base_args,
        valid_value=42,
        valid_value_2=3.14,
    )

    # Resolution is in steps of 0.25
    # Float values are funny, we cannot test 0.25 because check may 'round' that to 0.04999999999999716
    for v1 in [0, 0.01, 42, 3.14]:
        for valid_delta in [
            0,
            0.1,
            0.2,
            0.24,
            -0.1,
            -0.2,
            -0.24,
        ]:
            v2 = v1 + valid_delta

            if v2 > 0:  # Ensure value stays valid
                _assert_generic_evaluator_equivalent(*base_args, v1=v1, v2=v2)
        for invalid_delta in [
            0.26,
            1,
            42,
            -0.26,
            -1,
            -42,
        ]:
            v2 = v1 + invalid_delta

            if v2 > 0:  # Ensure value stays valid
                _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)


def test_evaluate_track():
    """Test the evaluate_track function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["track"] = value
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"current_state": {"track": value}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["current_state"] = {"track": value}
        return flight

    base_args = (
        "_evaluate_track",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=42,
        valid_value_2=3.14,
    )

    # Value should be in [0;360[ or the special 361 value
    for valid_value in [0, 0.01, 42, 3.14, 359, 361]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in [
        -0.01,
        -42,
        -3.14,
        -359,
        -361,
        -362,
        -1000,
        360,
        -360,
        377,
        1000,
    ]:
        _assert_generic_evaluator_invalid_value(
            *base_args, invalid_value=invalid_value, valid_value=42
        )

    _assert_generic_evaluator_dont_have_default(
        *base_args,
        valid_value=42,
        valid_value_2=3.14,
    )

    # Resolution is in steps of 1
    # Float values are funny, we cannot test 0.25 because check may 'round' that to 0.04999999999999716
    for v1 in [0, 42, 3.14, 100]:
        for valid_delta in [
            0,
            0.1,
            0.2,
            0.5,
            0.9,
            0.95,
            -0.1,
            -0.2,
            -0.5,
            -0.9,
            -0.95,
        ]:
            v2 = v1 + valid_delta

            if 0 <= v2 < 360:  # Ensure value stays valid
                _assert_generic_evaluator_equivalent(*base_args, v1=v1, v2=v2)
        for invalid_delta in [
            1.1,
            2,
            10,
            100,
        ]:
            v2 = v1 + invalid_delta

            if 0 <= v2 < 360:  # Ensure value stays valid
                _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)

    # Ensure special value doesn't interfer
    _assert_generic_evaluator_not_equivalent(*base_args, v1=1, v2=361)
    _assert_generic_evaluator_not_equivalent(*base_args, v1=361, v2=1)
    # Ensure special value is equal
    _assert_generic_evaluator_equivalent(*base_args, v1=361, v2=361)


def test_evaluate_timestamp():
    """Test the evaluate_timestamp function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["timestamp"] = value
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"current_state": {"timestamp": value}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["current_state"] = {"timestamp": value}
        return flight

    base_args = (
        "_evaluate_timestamp",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value="2025-01-01T12:00:00.0Z",
        valid_value_2="2025-02-02T14:00:00.0Z",
    )

    # Random valid timestamps
    for valid_value in [
        "2025-01-01T12:00:00.0Z",
        "2025-02-02T14:00:00.0Z",
        "2025-03-03T16:00:00Z",
        "2025-04-04T18:18:18.18Z",
    ]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in ["2000-01-01T12:00:00.0+07:00", "what time is it?"]:
        _assert_generic_evaluator_invalid_value(
            *base_args, invalid_value=invalid_value, valid_value=42
        )

    _assert_generic_evaluator_dont_have_default(
        *base_args,
        valid_value="2025-01-01T12:00:00.0Z",
        valid_value_2="2025-02-02T14:00:00.0Z",
    )

    _assert_generic_evaluator_equivalent(
        *base_args, v1="2025-01-01T12:00:00Z", v2="2025-01-01T12:00:00.05Z"
    )
    _assert_generic_evaluator_not_equivalent(
        *base_args, v1="2025-01-01T12:00:00Z", v2="2025-01-01T12:00:00.1Z"
    )
    _assert_generic_evaluator_not_equivalent(
        *base_args, v1="2025-01-01T12:00:00Z", v2="2025-01-01T12:00:01Z"
    )
    _assert_generic_evaluator_not_equivalent(
        *base_args, v1="2025-01-01T12:00:00Z", v2="2025-01-01T14:00:00Z"
    )
    _assert_generic_evaluator_not_equivalent(
        *base_args, v1="2025-01-01T12:00:00Z", v2="2025-01-02T12:00:00Z"
    )


def test_evaluate_height():
    """Test the evaluate_height function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["position"] = {"height": {"distance": value}}
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["height"] = {"distance": value}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["most_recent_position"] = {"height": {"distance": value}}
        return flight

    base_args = (
        "_evaluate_height",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=42,
        valid_value_2=3.14,
    )

    for valid_value in [0, 0.01, 42, 3.14, 359, 361, -361, -1000, -3.14]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    _assert_generic_evaluator_defaults(
        *base_args,
        default_value=-1000,
        valid_value=1000,
    )

    # Resolution is in steps of 1
    # Float values are funny, we cannot test 0.25 because check may 'round' that to 0.04999999999999716
    for v1 in [0, 42, 3.14, 100]:
        for valid_delta in [
            0,
            0.1,
            0.2,
            0.5,
            0.9,
            0.95,
            -0.1,
            -0.2,
            -0.5,
            -0.9,
            -0.95,
        ]:
            v2 = v1 + valid_delta
            _assert_generic_evaluator_equivalent(*base_args, v1=v1, v2=v2)
        for invalid_delta in [
            1.1,
            2,
            10,
            100,
            -1.1,
            -2,
            -10,
            -100,
        ]:
            v2 = v1 + invalid_delta
            _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)

    # Ensure special value doesn't interfer
    _assert_generic_evaluator_not_equivalent(*base_args, v1=-1000, v2=42)
    _assert_generic_evaluator_not_equivalent(*base_args, v1=42, v2=-1000)
    # Ensure special value is equal
    _assert_generic_evaluator_equivalent(*base_args, v1=-1000, v2=-1000)


def test_evaluate_height_type():
    """Test the evaluate_height_type function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["position"] = {"height": {"reference": value}}
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["height"] = {"reference": value}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["most_recent_position"] = {"height": {"reference": value}}
        return flight

    base_args = (
        "_evaluate_height_type",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=RIDHeightReference.GroundLevel,
        valid_value_2=RIDHeightReference.TakeoffLocation,
    )

    for valid_value in [
        "GroundLevel",
        "TakeoffLocation",
    ]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in ["Undergound", "InATunnel"]:
        _assert_generic_evaluator_invalid_value(
            *base_args,
            invalid_value=invalid_value,
            valid_value=RIDHeightReference.GroundLevel,
        )

    for v1, v2 in permutations(
        ["GroundLevel", "TakeoffLocation"],
        2,
    ):
        _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)


def test_evaluate_operational_status():
    """Test the evaluate_operational_status function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["operational_status"] = value
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"current_state": {"operational_status": value}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["current_state"] = {"operational_status": value}
        return flight

    base_args = (
        "_evaluate_operational_status",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=RIDOperationalStatus.Ground,
        valid_value_2=RIDOperationalStatus.Airborne,
    )

    for valid_value in [
        "Undeclared",
        "Ground",
        "Airborne",
    ]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in ["Undergound", "InATunnel"]:
        _assert_generic_evaluator_invalid_value(
            *base_args,
            invalid_value=invalid_value,
            valid_value=RIDOperationalStatus.Ground,
        )

    v22a_only_values = ["Emergency", "RemoteIDSystemFailure"]

    for v22a_only_value in v22a_only_values:

        _assert_generic_evaluator_valid_value(
            *base_args, valid_value=v22a_only_value, rid_version=RIDVersion.f3411_22a
        )
        _assert_generic_evaluator_invalid_value(
            *base_args,
            valid_value=RIDOperationalStatus.Ground,
            invalid_value=v22a_only_value,
            rid_version=RIDVersion.f3411_19,
        )

    _assert_generic_evaluator_defaults(
        *base_args,
        default_value=RIDOperationalStatus.Undeclared,
        valid_value=RIDOperationalStatus.Ground,
    )

    for v1, v2 in permutations(
        ["Undeclared", "Ground", "Airborne", "Emergency", "RemoteIDSystemFailure"],
        2,
    ):
        rid_version = (
            RIDVersion.f3411_22a
            if v1 in v22a_only_values or v2 in v22a_only_values
            else RIDVersion.f3411_19
        )

        _assert_generic_evaluator_not_equivalent(
            *base_args, v1=v1, v2=v2, rid_version=rid_version
        )


def test_evaluate_alt():
    """Test the evaluate_alt function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["position"] = {"alt": value}
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"current_state": {"position": {"alt": value}}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["most_recent_position"] = {"alt": value}
        return flight

    base_args = (
        "_evaluate_alt",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=42,
        valid_value_2=3.14,
    )

    # Value can be anything
    for valid_value in [0, 0.01, 42, 3.14, 10000, -1, -0.01, -0.05, -10000]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    _assert_generic_evaluator_dont_have_default(
        *base_args,
        valid_value=42,
        valid_value_2=3.14,
    )

    # Resolution is in steps of 1
    for v1 in [0, 0.01, 42, 3.14, 10000]:
        for valid_delta in [
            0,
            0.1,
            0.2,
            0.5,
            0.9,
            0.95,
            -0.1,
            -0.2,
            -0.5,
            -0.9,
            -0.95,
        ]:
            v2 = v1 + valid_delta

            if v2 > 0:  # Ensure value stays valid
                _assert_generic_evaluator_equivalent(*base_args, v1=v1, v2=v2)
        for invalid_delta in [
            1.1,
            2,
            42,
            -1.1,
            2,
            -42,
        ]:
            v2 = v1 + invalid_delta

            if v2 > 0:  # Ensure value stays valid
                _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)


def test_evaluate_accuracy_v():
    """Test the evaluate_accuracy_v function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["position"] = {"accuracy_v": value}
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"current_state": {"position": {"accuracy_v": value}}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["most_recent_position"] = {"accuracy_v": value}
        return flight

    base_args = (
        "_evaluate_accuracy_v",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=VerticalAccuracy.VA150mPlus,
        valid_value_2=VerticalAccuracy.VA150m,
    )

    for valid_value in [
        "VAUnknown",
        "VA150mPlus",
        "VA150m",
        "VA45m",
        "VA25m",
        "VA10m",
        "VA3m",
        "VA1m",
    ]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in ["MeasuredWithALaser", "+/- 5m", "HA10NM"]:
        _assert_generic_evaluator_invalid_value(
            *base_args,
            invalid_value=invalid_value,
            valid_value=VerticalAccuracy.VA150mPlus,
        )

    for v1, v2 in permutations(
        [
            "VAUnknown",
            "VA150mPlus",
            "VA150m",
            "VA45m",
            "VA25m",
            "VA10m",
            "VA3m",
            "VA1m",
        ],
        2,
    ):
        _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)


def test_evaluate_accuracy_h():
    """Test the evaluate_accuracy_h function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["position"] = {"accuracy_h": value}
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"current_state": {"position": {"accuracy_h": value}}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["most_recent_position"] = {"accuracy_h": value}
        return flight

    base_args = (
        "_evaluate_accuracy_h",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=HorizontalAccuracy.HA10NMPlus,
        valid_value_2=HorizontalAccuracy.HA2NM,
    )

    for valid_value in [
        "HAUnknown",
        "HA10NMPlus",
        "HA10NM",
        "HA4NM",
        "HA2NM",
        "HA1NM",
        "HA05NM",
        "HA03NM",
        "HA01NM",
        "HA005NM",
        "HA30m",
        "HA10m",
        "HA3m",
        "HA1m",
    ]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in ["MeasuredWithALaser", "+/- 5m", "VA45m"]:
        _assert_generic_evaluator_invalid_value(
            *base_args,
            invalid_value=invalid_value,
            valid_value=HorizontalAccuracy.HA10NMPlus,
        )

    for v1, v2 in permutations(
        [
            "HAUnknown",
            "HA10NMPlus",
            "HA10NM",
            "HA4NM",
            "HA2NM",
            "HA1NM",
            "HA05NM",
            "HA03NM",
            "HA01NM",
            "HA005NM",
            "HA30m",
            "HA10m",
            "HA3m",
            "HA1m",
        ],
        2,
    ):
        _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)


def test_evaluate_speed_accuracy():
    """Test the evaluate_speed_accuracy function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["speed_accuracy"] = value
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"current_state": {"speed_accuracy": value}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["current_state"] = {"speed_accuracy": value}
        return flight

    base_args = (
        "_evaluate_speed_accuracy",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=SpeedAccuracy.SA3mps,
        valid_value_2=SpeedAccuracy.SA10mpsPlus,
    )

    for valid_value in [
        "SAUnknown",
        "SA10mpsPlus",
        "SA10mps",
        "SA3mps",
        "SA1mps",
        "SA03mps",
    ]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in ["MeasuredWithALaser", "+/- 5m", "VA45m"]:
        _assert_generic_evaluator_invalid_value(
            *base_args,
            invalid_value=invalid_value,
            valid_value=SpeedAccuracy.SA10mps,
        )

    for v1, v2 in permutations(
        [
            "SAUnknown",
            "SA10mpsPlus",
            "SA10mps",
            "SA3mps",
            "SA1mps",
            "SA03mps",
        ],
        2,
    ):
        _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)


def test_evaluate_vertical_speed():
    """Test the evaluate_vertical_speed function"""

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["vertical_speed"] = value
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"current_state": {"vertical_speed": value}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["current_state"] = {"vertical_speed": value}
        return flight

    base_args = (
        "_evaluate_vertical_speed",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    _assert_generic_evaluator_correct_field_is_used(
        *base_args,
        valid_value=42,
        valid_value_2=3.14,
    )

    # Value should be between -62, 62 or the special 255 value
    for valid_value in [0, 0.01, 42, 3.14, 62, 63, -62, -42, -5]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in [-63, -62.5, -1000, 1000]:
        _assert_generic_evaluator_invalid_value(
            *base_args, invalid_value=invalid_value, valid_value=42
        )

    _assert_generic_evaluator_dont_have_default(
        *base_args,
        valid_value=42,
        valid_value_2=3.14,
    )

    # Resolution is in steps of 0.1
    for v1 in [0, 0.01, 42, 3.14]:
        for valid_delta in [
            0,
            0.01,
            0.02,
            0.09,
            -0.09,
            -0.02,
            -0.024,
        ]:
            v2 = v1 + valid_delta
            _assert_generic_evaluator_equivalent(*base_args, v1=v1, v2=v2)
        for invalid_delta in [
            0.11,
            1,
            42,
            -0.11,
            -1,
            -42,
        ]:
            v2 = v1 + invalid_delta

            if v2 > 0:  # Ensure value stays valid
                _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)


def test_evaluate_uas_id():
    """Test uas id base part, about the presence of at least one field in observed values"""

    def do_checkfor_uas_id_presence(sp_observed, rid_version):

        def step_under_test(self: UnitTestScenario):
            evaluator = RIDCommonDictionaryEvaluator(
                config=EvaluationConfiguration(),
                test_scenario=self,
                rid_version=rid_version,
            )

            evaluator._evaluate_uas_id(None, sp_observed, None, None, datetime.now())

        unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()

        reported_missing_uas_id = False

        for c in unit_test_scenario.get_report().cases:
            for step in c.steps:
                for failed_check in step.failed_checks:
                    if failed_check.summary == "UAS ID is missing":
                        reported_missing_uas_id = True

        return not reported_missing_uas_id

    # v19
    for v in range(0, 4):  # We activate or not 2 fields, 2^2 == 4

        class SpObservedV19(ImplicitDict):

            def __init__(self, v):

                if v & 0b1:
                    self.registration_id = "x"
                if v & 0b10:
                    self.serial_number = "x"

        assert do_checkfor_uas_id_presence(
            SpObservedV19(v), RIDVersion.f3411_19
        ) == bool(v)

    # v22
    for v in range(0, 16):  # We activate or not 4 field, 2^4 == 16

        class SpObservedV22a(ImplicitDict):

            def __init__(self, v):

                if v & 0b1:
                    self.registration_id = "x"
                if v & 0b10:
                    self.serial_number = "x"

                self.raw = {"uas_id": {}}
                if v & 0b100:
                    self.raw["uas_id"]["specific_session_id"] = "x"
                if v & 0b1000:
                    self.raw["uas_id"]["utm_id"] = "x"

        assert do_checkfor_uas_id_presence(
            SpObservedV22a(v), RIDVersion.f3411_22a
        ) == bool(v)


def test_evaluate_uas_id_serial_number():

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["uas_id"] = {"serial_number": value}
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["serial_number"] = value
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["uas"] = {"id": value}
        return flight

    base_args = (
        "_evaluate_uas_id_serial_number",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    for valid_value in [
        SerialNumber.generate_valid(),
        "LWBE53EGFG",
        "9M2WC3YKQN9YZ3EHW",
    ]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in ["42", "SERIAL3000"]:
        _assert_generic_evaluator_invalid_value(
            *base_args,
            invalid_value=invalid_value,
            valid_value=SerialNumber.generate_valid(),
        )


def test_evaluate_uas_id_registration_id():

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["uas_id"] = {"registration_id": value}
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["registration_id"] = value
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["uas"] = {"id": value}
        return flight

    base_args = (
        "_evaluate_uas_id_registration_id",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    for valid_value in ["HB.4242", "HB.2424", "F.FRANCE"]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in ["42", "SERIAL3000", "COUNTRY.NUMBER"]:
        _assert_generic_evaluator_invalid_value(
            *base_args, invalid_value=invalid_value, valid_value="HB.4242"
        )


def test_evaluate_uas_id_utm_id():

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["uas_id"] = {"utm_id": value}
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"uas_id": {"utm_id": value}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["uas"] = {"id": value}
        return flight

    base_args = (
        "_evaluate_uas_id_utm_id",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    for valid_value in [
        str(uuid.uuid4()),
        "00000000-0000-0000-0000-000000000000",
        "{12345678-1234-5678-1234-567812345678}",
        "12345678123456781234567812345678",
        "urn:uuid:12345678-1234-5678-1234-567812345678",
        "12345678-1234-5678-1234-567812345678",
    ]:
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for invalid_value in ["42", "test"]:
        _assert_generic_evaluator_invalid_value(
            *base_args, invalid_value=invalid_value, valid_value=str(uuid.uuid4())
        )

    for v1, v2 in permutations(
        [
            "00000000-0000-0000-0000-000000000000",
            "{12345678-1234-5678-1234-567812345678}",
            "12345678123456781234567812345678",
            "urn:uuid:12345678-1234-5678-1234-567812345678",
            "12345678-1234-5678-1234-567812345678",
        ],
        2,
    ):
        if "0000" in v1 or "0000" in v2:
            _assert_generic_evaluator_not_equivalent(*base_args, v1=v1, v2=v2)
        else:
            _assert_generic_evaluator_equivalent(*base_args, v1=v1, v2=v2)


def test_evaluate_uas_id_specific_session_id():

    def injected_field_setter(flight: Any, value: T) -> Any:
        flight["uas_id"] = {"specific_session_id": value}
        return flight

    def sp_field_setter(flight: Any, value: T) -> Any:
        flight["raw"] = {"uas_id": {"specific_session_id": value}}
        return flight

    def dp_field_setter(flight: Any, value: T) -> Any:
        flight["uas"] = {"id": value}
        return flight

    base_args = (
        "_evaluate_uas_id_specific_session_id",
        injected_field_setter,
        sp_field_setter,
        dp_field_setter,
    )

    for valid_value in [
        str(uuid.uuid4()),
        "42",
        "Test",
        "Hello",
    ]:  # Everything is valid
        _assert_generic_evaluator_valid_value(*base_args, valid_value=valid_value)

    for valid_value in [
        str(uuid.uuid4()),
        "42",
        "Test",
        "Hello",
    ]:  # If nothing is injected, everything is valid
        _assert_generic_evaluator_result(
            *base_args, None, valid_value, valid_value, outcome=True
        )
