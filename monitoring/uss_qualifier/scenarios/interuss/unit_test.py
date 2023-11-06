from typing import Callable
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioDeclaration
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class UnitTestScenario(GenericTestScenario):
    def __init__(self, step_under_test: Callable[["UnitTestScenario"], None]):
        self._allow_undocumented_checks = True
        self.step_under_test = step_under_test
        self.declaration = TestScenarioDeclaration(
            scenario_type="scenarios.interuss.unit_test.UnitTestScenario",
        )
        super().__init__()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.begin_test_case("Case under test")
        self.begin_test_step("Step under test")
        self.step_under_test(self)
        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()

    def execute_unit_test(self):
        context = ExecutionContext(None)
        self.run(context)
        self.cleanup()
        return self
