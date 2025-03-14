from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from implicitdict import ImplicitDict
from loguru import logger

from monitoring.uss_qualifier.action_generators.definitions import (
    ActionGeneratorDefinition,
)
from monitoring.uss_qualifier.fileio import FileReference, load_dict_with_references
from monitoring.uss_qualifier.reports.capability_definitions import (
    ParticipantCapabilityDefinition,
)
from monitoring.uss_qualifier.resources.definitions import (
    ResourceDeclaration,
    ResourceID,
    ResourceTypeName,
)
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioDeclaration

TestSuiteTypeName = FileReference


class TestSuiteDeclaration(ImplicitDict):
    suite_type: Optional[TestSuiteTypeName]
    """Type/location of test suite.  Usually expressed as the file name of the suite definition (without extension) qualified relative to the `uss_qualifier` folder"""

    suite_definition: Optional[TestSuiteDefinition]
    """Definition of test suite internal to the configuration -- specified instead of `suite_type`."""

    resources: Optional[Dict[ResourceID, ResourceID]]
    """Mapping of the ID a resource will be known by in the child test suite -> the ID a resource is known by in the parent test suite.

    The child suite resource <key> is supplied by the parent suite resource <value>.
    """

    def __init__(self, *args, **kwargs):
        super(TestSuiteDeclaration, self).__init__(*args, **kwargs)
        if (
            "suite_type" in self
            and self.suite_type
            and "suite_definition" in self
            and self.suite_definition
        ):
            raise ValueError(
                f"May not specify both suite_type ({self.suite_type}) and suite_definition (name='{self.suite_definition.name}') in the same TestSuiteDeclaration"
            )
        if ("suite_type" not in self or not self.suite_type) and (
            "suite_definition" not in self or not self.suite_definition
        ):
            raise ValueError(
                "Must specify either suite_type or suite_definition in TestSuiteDeclaration"
            )

    @property
    def type_name(self) -> str:
        if "suite_type" in self and self.suite_type:
            return self.suite_type
        else:
            return "<in-configuration definition>"


class ReactionToFailure(str, Enum):
    Continue = "Continue"
    """If the test suite action fails, continue to the next action in that test suite"""

    Abort = "Abort"
    """If the test suite action fails, do not execute any more actions in that test suite"""


class ActionType(str, Enum):
    TestScenario = "test_scenario"
    TestSuite = "test_suite"
    ActionGenerator = "action_generator"

    @staticmethod
    def raise_invalid_action_declaration():
        raise ValueError(
            f"Exactly one of ({', '.join(a for a in ActionType)}) must be specified in a TestSuiteActionDeclaration"
        )


class TestSuiteActionDeclaration(ImplicitDict):
    """Defines a step in the sequence of things to do for a test suite.

    Exactly one of `test_scenario`, `test_suite`, or `action_generator` must be specified.
    """

    test_scenario: Optional[TestScenarioDeclaration]
    """If this field is populated, declaration of the test scenario to run"""

    test_suite: Optional[TestSuiteDeclaration]
    """If this field is populated, declaration of the test suite to run"""

    action_generator: Optional[ActionGeneratorDefinition]
    """If this field is populated, declaration of a generator that will produce 0 or more test suite actions"""

    on_failure: ReactionToFailure = ReactionToFailure.Continue
    """What to do if this action fails"""

    def get_action_type(self) -> ActionType:
        matches = [v for v in ActionType if v in self and self[v]]
        if len(matches) != 1:
            ActionType.raise_invalid_action_declaration()
        return ActionType(matches[0])

    def get_resource_links(self) -> Dict[ResourceID, ResourceID]:
        action_type = self.get_action_type()
        if action_type == ActionType.TestScenario:
            return self.test_scenario.resources
        elif action_type == ActionType.TestSuite:
            return self.test_suite.resources
        elif action_type == ActionType.ActionGenerator:
            return self.action_generator.resources
        else:
            ActionType.raise_invalid_action_declaration()

    def get_child_type(self) -> str:
        action_type = self.get_action_type()
        if action_type == ActionType.TestScenario:
            return self.test_scenario.scenario_type
        elif action_type == ActionType.TestSuite:
            return self.test_suite.type_name
        elif action_type == ActionType.ActionGenerator:
            return self.action_generator.generator_type
        else:
            ActionType.raise_invalid_action_declaration()


ResourceTypeNameSpecifyingOptional = ResourceTypeName
"""This string is a ResourceTypeName, but then may be suffixed with '?'.  If the value ends in '?', that indicates the resource is optional and does not need to be provided."""


class TestSuiteDefinition(ImplicitDict):
    """Schema for the definition of a test suite, analogous to the Python TestScenario subclass for scenarios"""

    name: str
    """Name of the test suite"""

    resources: Dict[ResourceID, ResourceTypeNameSpecifyingOptional]
    """Enumeration of the resources used by this test suite"""

    local_resources: Optional[Dict[ResourceID, ResourceDeclaration]]
    """Declarations of resources originating in this test suite.  If a resource is defined in both `resources` and `local_resources`, the resource in `local_resources` will be ignored (`resources` overrides `local_resources`)."""

    actions: List[TestSuiteActionDeclaration]
    """The actions to take when running the test suite.  Components will be executed in order."""

    participant_verifiable_capabilities: Optional[List[ParticipantCapabilityDefinition]]
    """Definitions of capabilities verified by this test suite for individual participants."""

    @staticmethod
    def load_from_declaration(
        declaration: TestSuiteDeclaration,
    ) -> TestSuiteDefinition:
        if "suite_type" in declaration:
            return ImplicitDict.parse(
                load_dict_with_references(declaration.suite_type), TestSuiteDefinition
            )
        elif "suite_definition" in declaration:
            return declaration.suite_definition
        else:
            raise ValueError(
                "Neither suite_type nor suite_definition were specified in TestSuiteDefinition"
            )
