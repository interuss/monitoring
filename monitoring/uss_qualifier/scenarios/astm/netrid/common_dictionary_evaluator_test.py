from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.scenarios.interuss.unit_test import UnitTestScenario
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.scenarios.astm.netrid.common_dictionary_evaluator import (
    RIDCommonDictionaryEvaluator,
)


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
