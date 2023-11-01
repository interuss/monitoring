from typing import Optional

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.action_generators.definitions import GeneratorTypeName
from monitoring.uss_qualifier.fileio import FileReference
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioTypeName
from monitoring.uss_qualifier.suites.definitions import (
    ActionType,
    TestSuiteDefinition,
    TestSuiteTypeName,
)


class PotentialTestScenarioAction(ImplicitDict):
    scenario_type: TestScenarioTypeName
    """Type of test scenario."""


class PotentialTestSuiteAction(ImplicitDict):
    suite_type: Optional[TestSuiteTypeName]
    """Type/location of test suite.  Usually expressed as the file name of the suite definition (without extension) qualified relative to the `uss_qualifier` folder"""

    suite_definition: Optional[TestSuiteDefinition]
    """Definition of test suite internal to the configuration -- specified instead of `suite_type`."""


class PotentialActionGeneratorAction(ImplicitDict):
    generator_type: GeneratorTypeName
    """Type of action generator."""

    specification: dict
    """Specification of action generator; format is the ActionGeneratorSpecificationType that corresponds to the `generator_type`"""


class PotentialGeneratedAction(ImplicitDict):
    test_scenario: Optional[PotentialTestScenarioAction]
    test_suite: Optional[PotentialTestSuiteAction]
    action_generator: Optional[PotentialActionGeneratorAction]

    def get_action_type(self) -> ActionType:
        matches = [v for v in ActionType if v in self and self[v]]
        if len(matches) != 1:
            ActionType.raise_invalid_action_declaration()
        return ActionType(matches[0])
