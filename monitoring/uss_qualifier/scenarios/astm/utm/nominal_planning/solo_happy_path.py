from deprecation import deprecated

from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class SoloHappyPath(TestScenario):
    @deprecated(deprecated_in="0.26.0")
    def run(self, context):
        self.begin_test_scenario(context)
        self.end_test_scenario()
