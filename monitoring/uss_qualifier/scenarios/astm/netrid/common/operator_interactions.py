from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class OperatorInteractions(GenericTestScenario):
    def __init__(self):
        super().__init__()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        # TODO: Implement
        self.end_test_scenario()
