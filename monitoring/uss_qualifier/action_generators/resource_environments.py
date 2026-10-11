from collections.abc import Iterator

from implicitdict import ImplicitDict

from monitoring.monitorlib.inspection import fullname
from monitoring.uss_qualifier.action_generators.action_generator import ActionGenerator
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_declaration,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.environments import (
    ResourceEnvironmentsGenerator,
)
from monitoring.uss_qualifier.resources.resource import (
    MissingResourceError,
    ResourceType,
)
from monitoring.uss_qualifier.suites.definitions import TestSuiteActionDeclaration
from monitoring.uss_qualifier.suites.suite import TestSuiteAction


class ResourceEnvironmentsActionGeneratorSpecification(ImplicitDict):
    action_to_repeat: TestSuiteActionDeclaration
    """Test suite action to run for each resource environment"""

    resource_environments_source: ResourceID
    """Resource providing different resource environments"""


class ResourceEnvironmentsActionGenerator(
    ActionGenerator[ResourceEnvironmentsActionGeneratorSpecification]
):
    _actions: list[TestSuiteAction]
    _current_action: int

    @classmethod
    def list_potential_actions(
        cls, specification: ResourceEnvironmentsActionGeneratorSpecification | None
    ) -> list[PotentialGeneratedAction]:
        if specification is None:
            raise ValueError(f"{cls.__name__} requires a specification")
        return list_potential_actions_for_action_declaration(
            specification.action_to_repeat
        )

    @classmethod
    def get_name(cls) -> str:
        return "For each resource environment"

    def __init__(
        self,
        specification: ResourceEnvironmentsActionGeneratorSpecification,
        resources: dict[ResourceID, ResourceType],
    ):
        if specification.resource_environments_source not in resources:
            raise MissingResourceError(
                f"Resource ID {specification.resource_environments_source} specified as `resource_environments_source` was not present in the available resource pool",
                specification.resource_environments_source,
            )
        environments_source = resources[specification.resource_environments_source]
        if not isinstance(environments_source, ResourceEnvironmentsGenerator):
            raise ValueError(
                f"Expected resource ID {specification.resource_environments_source} to be a {fullname(ResourceEnvironmentsGenerator)} but it was a {fullname(environments_source.__class__)} instead"
            )

        self._actions = []
        for resource_env in environments_source.get_environments():
            modified_resources = resources | resource_env

            self._actions.append(
                TestSuiteAction(specification.action_to_repeat, modified_resources)
            )

        self._current_action = 0

    def actions(self) -> Iterator[TestSuiteAction]:
        yield from self._actions
