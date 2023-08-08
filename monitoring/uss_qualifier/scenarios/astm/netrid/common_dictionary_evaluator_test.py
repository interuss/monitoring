from typing import List, Tuple
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.scenarios.astm.netrid.common_dictionary_evaluator import (
    RIDCommonDictionaryEvaluator,
)
from monitoring.uss_qualifier.scenarios.interuss.unit_test import UnitTestScenario
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from uas_standards.astm.f3411.v22a.api import Altitude, LatLngPoint, OperatorLocation


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
