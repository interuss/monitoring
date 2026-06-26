from collections.abc import Iterator

from implicitdict import ImplicitDict, Optional

from monitoring.monitorlib.inspection import fullname
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_declaration,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.flight_planning import FlightPlannersResource
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerCombinationSelectorResource,
    FlightPlannerCombinationSelectorSpecification,
)
from monitoring.uss_qualifier.resources.resource import (
    MissingResourceError,
    ResourceProvidingResource,
    ResourceType,
)
from monitoring.uss_qualifier.suites.definitions import TestSuiteActionDeclaration
from monitoring.uss_qualifier.suites.suite import ActionGenerator, TestSuiteAction


class FlightPlannerCombinationsSpecification(ImplicitDict):
    action_to_repeat: TestSuiteActionDeclaration
    """Test suite action to run for each combination of flight planners"""

    flight_planners_source: ResourceID
    """ID of the resource providing all available flight planners"""

    combination_selector_source: Optional[ResourceID] = None
    """If specified and contained in the provided resources, the resource containing a FlightPlannerCombinationSelectorResource to select only a subset of combinations"""

    roles: list[ResourceID]
    """Resource IDs of FlightPlannerResource inputs to the action_to_repeat"""


class FlightPlannerCombinations(
    ActionGenerator[FlightPlannerCombinationsSpecification]
):
    _actions_with_participants: list[tuple[TestSuiteAction, frozenset[str]]]
    _current_action: int

    @classmethod
    def list_potential_actions(
        cls, specification: FlightPlannerCombinationsSpecification
    ) -> list[PotentialGeneratedAction]:
        return list_potential_actions_for_action_declaration(
            specification.action_to_repeat
        )

    @classmethod
    def get_name(cls) -> str:
        return "For each appropriate combination of flight planner(s)"

    def __init__(
        self,
        specification: FlightPlannerCombinationsSpecification,
        resources: dict[ResourceID, ResourceType],
    ):
        if specification.flight_planners_source not in resources:
            raise MissingResourceError(
                f"Resource ID {specification.flight_planners_source} specified as `flight_planners_source` was not present in the available resource pool",
                specification.flight_planners_source,
            )
        flight_planners_resource: FlightPlannersResource = resources[
            specification.flight_planners_source
        ]
        if not isinstance(flight_planners_resource, FlightPlannersResource):
            raise ValueError(
                f"Expected resource ID {specification.flight_planners_source} to be a {fullname(FlightPlannersResource)} but it was a {fullname(flight_planners_resource.__class__)} instead"
            )
        flight_planners = flight_planners_resource.flight_planners

        if (
            specification.combination_selector_source is not None
            and specification.combination_selector_source in resources
        ):
            combination_selector = resources[specification.combination_selector_source]
            if not isinstance(
                combination_selector, FlightPlannerCombinationSelectorResource
            ):
                raise ValueError(
                    f"Expected resource ID {specification.combination_selector_source} to be a {fullname(FlightPlannerCombinationSelectorResource)} but it was a {fullname(combination_selector.__class__)} instead"
                )
        else:
            combination_selector = FlightPlannerCombinationSelectorResource(
                FlightPlannerCombinationSelectorSpecification(),
                "default flight planner combination selector",
            )

        self._actions_with_participants = []
        role_assignments = [0] * len(specification.roles)
        combination_index = 0
        while True:
            participants = flight_planners_resource.make_subset(role_assignments)
            flight_planners_combination = {
                k: v for k, v in zip(specification.roles, participants)
            }

            if combination_selector.is_valid_combination(flight_planners_combination):
                modified_resources = {
                    k: v.provide_resource_for(index=combination_index)
                    if isinstance(v, ResourceProvidingResource)
                    else v
                    for k, v in resources.items()
                }
                for k, v in flight_planners_combination.items():
                    modified_resources[k] = v

                self._actions_with_participants.append(
                    (
                        TestSuiteAction(
                            specification.action_to_repeat, modified_resources
                        ),
                        frozenset(p.participant_id for p in participants),
                    )
                )
                combination_index += 1

            index_to_increment = len(role_assignments) - 1
            while index_to_increment >= 0:
                role_assignments[index_to_increment] += 1
                if role_assignments[index_to_increment] >= len(flight_planners):
                    role_assignments[index_to_increment] = 0
                    index_to_increment -= 1
                else:
                    break
            if index_to_increment < 0:
                break

        self._current_action = 0

    def actions(
        self,
    ) -> Iterator[TestSuiteAction] | Iterator[list[list[TestSuiteAction]]]:
        for action, _ in self._actions_with_participants:
            yield action


class ParallelFlightPlannerCombinations(FlightPlannerCombinations):
    """Like FlightPlannerCombinations, but yields actions grouped so actions
    sharing no participant run in parallel."""

    @classmethod
    def get_name(cls) -> str:
        return "For each appropriate combination of flight planner(s), in parallel where possible"

    def actions(self) -> Iterator[list[list[TestSuiteAction]]]:
        # Greedy first-fit grouping
        groups: list[list[tuple[TestSuiteAction, frozenset[str]]]] = []
        for action, participants in self._actions_with_participants:
            for group in groups:
                used = frozenset().union(*(p for _, p in group))
                if used.isdisjoint(participants):
                    group.append((action, participants))
                    break
            else:
                groups.append([(action, participants)])

        for group in groups:
            yield [[action] for action, _ in group]
