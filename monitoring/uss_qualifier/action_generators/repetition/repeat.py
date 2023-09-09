from typing import Dict, List, Optional

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_declaration,
)
from monitoring.uss_qualifier.reports.report import TestSuiteActionReport
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.resource import ResourceType

from monitoring.uss_qualifier.suites.definitions import TestSuiteActionDeclaration
from monitoring.uss_qualifier.suites.suite import (
    ActionGenerator,
    TestSuiteAction,
    ReactionToFailure,
)


class RepeatSpecification(ImplicitDict):
    action_to_repeat: TestSuiteActionDeclaration
    """Test suite action to repeat"""

    times_to_repeat: int
    """Number of times to repeat the test suite action declared above"""


class Repeat(ActionGenerator[RepeatSpecification]):
    _actions: List[TestSuiteAction]
    _current_action: int
    _failure_reaction: ReactionToFailure

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
        self._failure_reaction = specification.action_to_repeat.on_failure

    def run_next_action(self) -> Optional[TestSuiteActionReport]:
        if self._current_action < len(self._actions):
            report = self._actions[self._current_action].run()
            self._current_action += 1
            if not report.successful():
                if self._failure_reaction == ReactionToFailure.Abort:
                    self._current_action = len(self._actions)
            return report
        else:
            return None
