"""This is a separate file, to allow a specifc scenario definition, without a cleanup entry in the documentation"""

from monitoring.uss_qualifier.scenarios.scenario import TestScenario as _TestScenario
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenarioDeclaration as _TestScenarioDeclaration,
)


def build_generic_test_scenario_instance_without_cleanup() -> _TestScenario:
    """Return a GenericTestScenario instance that can be used to test various methods, with definition without cleanup"""

    declaration = _TestScenarioDeclaration(
        scenario_type="scenarios.test.GenericTestScenarioForTests"
    )

    class GenericTestScenarioForTestsWihoutCleanup(_TestScenario):
        def run(self, context):
            pass

    gtsi = GenericTestScenarioForTestsWihoutCleanup()
    gtsi.declaration = declaration
    gtsi.resource_origins = {}

    return gtsi
