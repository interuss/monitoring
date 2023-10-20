from typing import Dict, List, Iterator

from implicitdict import ImplicitDict

from monitoring.monitorlib.inspection import fullname
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_declaration,
)
from monitoring.uss_qualifier.resources.astm.f3548.v21 import (
    DSSInstancesResource,
    DSSInstanceResource,
)

from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.resource import (
    ResourceType,
    MissingResourceError,
)
from monitoring.uss_qualifier.suites.definitions import TestSuiteActionDeclaration
from monitoring.uss_qualifier.suites.suite import (
    ActionGenerator,
    TestSuiteAction,
)


class ForEachDSSSpecification(ImplicitDict):
    action_to_repeat: TestSuiteActionDeclaration
    """Test suite action to run for each DSS instance"""

    dss_instances_source: ResourceID
    """ID of the resource providing the single DSS instance"""

    dss_instance_id: ResourceID
    """Resource IDs of DSS input to the action_to_repeat"""


class ForEachDSS(ActionGenerator[ForEachDSSSpecification]):
    _actions: List[TestSuiteAction]
    _current_action: int

    @classmethod
    def list_potential_actions(
        cls, specification: ForEachDSSSpecification
    ) -> List[PotentialGeneratedAction]:
        return list_potential_actions_for_action_declaration(
            specification.action_to_repeat
        )

    @classmethod
    def get_name(cls) -> str:
        return "For each F3548 DSS instance"

    def __init__(
        self,
        specification: ForEachDSSSpecification,
        resources: Dict[ResourceID, ResourceType],
    ):
        if specification.dss_instances_source not in resources:
            raise MissingResourceError(
                f"Resource ID {specification.dss_instances_source} specified as `dss_instances_source` was not present in the available resource pool",
                specification.dss_instances_source,
            )
        dss_instances_resource: DSSInstancesResource = resources[
            specification.dss_instances_source
        ]
        if not isinstance(dss_instances_resource, DSSInstancesResource):
            raise ValueError(
                f"Expected resource ID {specification.dss_instances_source} to be a {fullname(DSSInstancesResource)} but it was a {fullname(dss_instances_resource.__class__)} instead"
            )
        dss_instances = dss_instances_resource.dss_instances

        self._actions = []
        for dss_instance in dss_instances:
            modified_resources = {k: v for k, v in resources.items()}
            modified_resources[
                specification.dss_instance_id
            ] = DSSInstanceResource.from_dss_instance(dss_instance)

            self._actions.append(
                TestSuiteAction(specification.action_to_repeat, modified_resources)
            )

        self._current_action = 0

    def actions(self) -> Iterator[TestSuiteAction]:
        for a in self._actions:
            yield a
