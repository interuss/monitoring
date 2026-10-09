from collections.abc import Iterator
from dataclasses import dataclass
from typing import Optional

from implicitdict import ImplicitDict

from monitoring.monitorlib.inspection import fullname
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.environments import (
    ResourceEnvironmentSelectorResource,
    ResourceEnvironmentsGenerator,
)
from monitoring.uss_qualifier.resources.plural import PluralResource
from monitoring.uss_qualifier.resources.resource import Resource


class ResourceCombinationsSpecification(ImplicitDict):
    pass


@dataclass
class _RoleCombination:
    role: ResourceID
    resources: PluralResource
    index: int


class ResourceCombinationsResource(
    ResourceEnvironmentsGenerator, Resource[ResourceCombinationsSpecification]
):
    """Resource that produces combinations of each dependent PluralResource according to ResourceIDs assigned by dependent resource keys.

    For example, with a pre-existing dependent `flight_planners` FlightPlannersResource, a
    ResourceCombinationsResource(tested_uss=flight_planners, control_uss=flight_planners) will produce each combination
    of tested_uss=FP1, control_uss=FP2 for all FP1, FP2 combinations in flight_planners.
    """

    _resource_sources: dict[ResourceID, PluralResource]
    _selector: Optional[ResourceEnvironmentSelectorResource]

    def __init__(
        self,
        specification: ResourceCombinationsSpecification,
        resource_origin: str,
        combination_selector: Optional[ResourceEnvironmentSelectorResource] = None,
        **dependencies,
    ):
        super().__init__(specification, resource_origin)
        self._selector = combination_selector
        self._resource_sources = dict()
        for k, v in dependencies.items():
            if not isinstance(v, PluralResource):
                raise ValueError(
                    f"Dependent resources for ResourceCombinationsResource must be PluralResources; dependent resource '{k}' was instead a {fullname(v.__class__)}"
                )
            if v.get_resource_instances_count() == 0:
                # Can't fill this role because there are no resources to fill it with.
                continue
            self._resource_sources[ResourceID(k)] = v

    def get_environments(self) -> Iterator[dict[ResourceID, Resource]]:
        """Get the combinations of resources fulfilling each specified role."""
        roles = [
            _RoleCombination(role=k, resources=v, index=0)
            for k, v in self._resource_sources.items()
        ]

        incremented = True
        while incremented:
            combination = {
                role.role: role.resources.get_resource_instance(role.index)
                for role in roles
            }
            if self._selector is None or self._selector.select_resource_environment(
                combination
            ):
                yield combination

            incremented = False
            for r in range(len(roles)):
                if (
                    roles[r].index
                    < roles[r].resources.get_resource_instances_count() - 1
                ):
                    roles[r].index += 1
                    for r0 in range(r):
                        roles[r0].index = 0
                    incremented = True
                    break
