from typing import Dict, List, Iterator

from implicitdict import ImplicitDict
from monitoring.monitorlib.inspection import fullname
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
    PotentialTestScenarioAction,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_declaration,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSsResource
from monitoring.uss_qualifier.resources.interuss.mock_uss.locality import (
    LocalityResource,
)
from monitoring.uss_qualifier.resources.resource import ResourceType
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioDeclaration
from monitoring.uss_qualifier.scenarios.interuss.mock_uss.configure_locality import (
    ConfigureLocality,
)
from monitoring.uss_qualifier.scenarios.interuss.mock_uss.unconfigure_locality import (
    UnconfigureLocality,
)
from monitoring.uss_qualifier.scenarios.scenario import get_scenario_type_name

from monitoring.uss_qualifier.suites.definitions import TestSuiteActionDeclaration
from monitoring.uss_qualifier.suites.suite import (
    ActionGenerator,
    TestSuiteAction,
    ReactionToFailure,
)


class WithLocalitySpecification(ImplicitDict):
    action_to_wrap: TestSuiteActionDeclaration
    """Test suite action to perform after setting mock_uss localities"""

    mock_uss_instances_source: ResourceID
    """ID of the resource providing all mock_uss instances to change the locality of"""

    locality_source: ResourceID
    """ID of the resource providing the locality to use temporarily for the provided mock_uss instances"""


class WithLocality(ActionGenerator[WithLocalitySpecification]):
    """Performs a specified test suite action after first configuring mock_uss instances to use a specified locality,
    and then restoring the original locality afterward."""

    _actions: List[TestSuiteAction]
    _current_action: int

    @classmethod
    def list_potential_actions(
        cls, specification: WithLocalitySpecification
    ) -> List[PotentialGeneratedAction]:
        actions = [
            PotentialGeneratedAction(
                test_scenario=PotentialTestScenarioAction(
                    scenario_type=get_scenario_type_name(ConfigureLocality)
                )
            )
        ]
        actions.extend(
            list_potential_actions_for_action_declaration(specification.action_to_wrap)
        )
        actions.append(
            PotentialGeneratedAction(
                test_scenario=PotentialTestScenarioAction(
                    scenario_type=get_scenario_type_name(UnconfigureLocality)
                )
            )
        )
        return actions

    @classmethod
    def get_name(cls) -> str:
        return "With mock_uss instances configured for a locality"

    def __init__(
        self,
        specification: WithLocalitySpecification,
        resources: Dict[ResourceID, ResourceType],
    ):
        if specification.mock_uss_instances_source not in resources:
            raise ValueError(
                f"Missing mock_uss_instances_source resource ID '{specification.mock_uss_instances_source}' in resource pool"
            )
        if not isinstance(
            resources[specification.mock_uss_instances_source], MockUSSsResource
        ):
            raise ValueError(
                f"mock_uss_instances_source resource '{specification.mock_uss_instances_source}' is a {fullname(type(resources[specification.mock_uss_instances_source]))} rather than the expected {fullname(MockUSSsResource)}"
            )
        if specification.locality_source not in resources:
            raise ValueError(
                f"Missing locality_source resource ID '{specification.locality_source}' in resource pool"
            )
        if not isinstance(resources[specification.locality_source], LocalityResource):
            raise ValueError(
                f"locality_source resource '{specification.locality_source}' is a {fullname(type(resources[specification.locality_source]))} rather than the expected {fullname(LocalityResource)}"
            )

        # Continue to unconfigure localities even for failure in the main action
        action_to_wrap = ImplicitDict.parse(
            specification.action_to_wrap, TestSuiteActionDeclaration
        )
        action_to_wrap.on_failure = ReactionToFailure.Continue

        self._actions = [
            TestSuiteAction(
                TestSuiteActionDeclaration(
                    test_scenario=TestScenarioDeclaration(
                        scenario_type=get_scenario_type_name(ConfigureLocality),
                        resources={
                            "mock_uss_instances": specification.mock_uss_instances_source,
                            "locality": specification.locality_source,
                        },
                    ),
                    on_failure=ReactionToFailure.Abort,
                ),
                resources,
            ),
            TestSuiteAction(action_to_wrap, resources),
            TestSuiteAction(
                TestSuiteActionDeclaration(
                    test_scenario=TestScenarioDeclaration(
                        scenario_type=get_scenario_type_name(UnconfigureLocality),
                        resources={},
                    ),
                    on_failure=ReactionToFailure.Continue,
                ),
                resources,
            ),
        ]
        self._current_action = 0

    def actions(self) -> Iterator[TestSuiteAction]:
        for a in self._actions:
            yield a
