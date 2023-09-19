from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class Scenario2(TestScenario):
    def __init__(self):
        super().__init__()

    def run(self):
        self.begin_test_scenario()
        # TODO: Implement

        # Perform one example check
        self.begin_test_case("Steps 4-6 for Part 107")
        self.begin_test_step("Retrieve pre-existing LAANC authorizations")
        with self.check(
            "LAANC authorizations obtained successfully", ["USS1"]
        ) as check:
            pass  # Check automatically passes if check.record_failed is not called
        self.end_test_step()
        self.end_test_case()

        self.end_test_scenario()
