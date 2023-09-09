from typing import Dict, List, Optional

from implicitdict import ImplicitDict

from monitoring.monitorlib.inspection import fullname
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_declaration,
)
from monitoring.uss_qualifier.reports.report import TestSuiteActionReport
from monitoring.uss_qualifier.resources.astm.f3411 import (
    DSSInstanceResource,
    DSSInstancesResource,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.resource import ResourceType
from monitoring.uss_qualifier.suites.definitions import TestSuiteActionDeclaration
from monitoring.uss_qualifier.suites.suite import (
    ActionGenerator,
    TestSuiteAction,
    ReactionToFailure,
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
    _failure_reaction: ReactionToFailure

    @classmethod
    def list_potential_actions(
        cls, specification: ForEachDSSSpecification
    ) -> List[PotentialGeneratedAction]:
        return list_potential_actions_for_action_declaration(
            specification.action_to_repeat
        )

    def __init__(
        self,
        specification: ForEachDSSSpecification,
        resources: Dict[ResourceID, ResourceType],
    ):
        if specification.dss_instances_source not in resources:
            raise ValueError(
                f"Resource ID {specification.dss_instances_source} specified as `dss_instances` was not present in the available resource pool"
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
