from typing import Dict, List, Iterator

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_declaration,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.resource import ResourceType

from monitoring.uss_qualifier.suites.definitions import TestSuiteActionDeclaration
from monitoring.uss_qualifier.suites.suite import (
    ActionGenerator,
    TestSuiteAction,
)


class RepeatSpecification(ImplicitDict):
    action_to_repeat: TestSuiteActionDeclaration
    """Test suite action to repeat"""

    times_to_repeat: int
    """Number of times to repeat the test suite action declared above"""


class Repeat(ActionGenerator[RepeatSpecification]):
    _actions: List[TestSuiteAction]
    _current_action: int

    @classmethod
    def list_potential_actions(
        cls, specification: RepeatSpecification
    ) -> List[PotentialGeneratedAction]:
        return list_potential_actions_for_action_declaration(
            specification.action_to_repeat
        )

    def __init__(
        self,
        specification: RepeatSpecification,
        resources: Dict[ResourceID, ResourceType],
    ):
        self._actions = [
            TestSuiteAction(specification.action_to_repeat, resources)
            for _ in range(specification.times_to_repeat)
        ]
        self._current_action = 0

    def actions(self) -> Iterator[TestSuiteAction]:
        for a in self._actions:
            yield a
