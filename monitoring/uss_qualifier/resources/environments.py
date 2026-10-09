from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Optional

from implicitdict import ImplicitDict

from monitoring.monitorlib.inspection import fullname
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.resource import (
    Resource,
    ResourceProvidingResource,
    ValueResource,
)


class ResourceEnvironmentsGenerator(ABC):
    @abstractmethod
    def get_environments(self) -> Iterator[dict[ResourceID, Resource]]:
        raise NotImplementedError()


class ResourceEnvironmentSelectorSpecification(ImplicitDict):
    """Specification defining how resource environments should be selected from the available/generated environments."""

    pass


class ResourceEnvironmentSelectorResource(
    ValueResource[ResourceEnvironmentSelectorSpecification]
):
    def select_resource_environment(
        self, resource_environment: dict[ResourceID, Resource]
    ) -> bool:
        """Returns True when the specified environment should be selected/used."""
        return True


class EnvironmentAugmentationResourceSpecification(ImplicitDict):
    # In the future, this specification could be enhanced to affect how and whether providers are exercised.
    pass


class EnvironmentAugmentationResource(
    ResourceEnvironmentsGenerator,
    Resource[EnvironmentAugmentationResourceSpecification],
):
    """Presents as a ResourceEnvironmentsGenerator which augments the environments from an input `environments` resource
    with additional resources named according to additional ResourceProvidingResource resource dependencies."""

    _environment_generator: ResourceEnvironmentsGenerator
    _providers: dict[ResourceID, ResourceProvidingResource]

    def __init__(
        self,
        specification: EnvironmentAugmentationResourceSpecification,
        resource_origin: str,
        environments: ResourceEnvironmentsGenerator,
        **providers,
    ):
        super().__init__(specification, resource_origin)

        if not isinstance(environments, ResourceEnvironmentsGenerator):
            raise ValueError(
                f"The `provider` resource dependency for an {self.__class__.__name__} must be a ResourceEnvironmentsGenerator; found instead a {fullname(environments.__class__)}"
            )
        self._environment_generator = environments

        self._providers = dict()
        for k, v in providers.items():
            if not isinstance(v, ResourceProvidingResource):
                raise ValueError(
                    f"All non-`provider` resource dependencies for an {self.__class__.__name__} must be ResourceProvidingResources, but the '{k}' resource dependency was instead a {fullname(environments.__class__)}"
                )
            self._providers[ResourceID(k)] = v

    def get_environments(self) -> Iterator[dict[ResourceID, Resource]]:
        for i, environment in enumerate(self._environment_generator.get_environments()):
            augmentation = dict()
            for resource_id, provider in self._providers.items():
                augmentation[resource_id] = provider.provide_resource_for(
                    index=i, environment=environment
                )
            yield environment | augmentation


class ConcatenatedResourceEnvironmentsResourceSpecification(ImplicitDict):
    environments_sequence: Optional[list[ResourceID]]
    """Sequence in which each dependent ResourceEnvironmentsGenerator resource's environments are enumerated."""


class ConcatenatedResourceEnvironmentsResource(
    ResourceEnvironmentsGenerator,
    Resource[ConcatenatedResourceEnvironmentsResourceSpecification],
):
    """Presents as a ResourceEnvironmentsGenerator which sequentially enumerates the environments from each dependent
    resource in the specified sequence."""

    _generators: list[ResourceEnvironmentsGenerator]

    def __init__(
        self,
        specification: ConcatenatedResourceEnvironmentsResourceSpecification,
        resource_origin: str,
        **generators,
    ):
        super().__init__(specification, resource_origin)

        for k, v in generators.items():
            if not isinstance(v, ResourceEnvironmentsGenerator):
                raise ValueError(
                    f"All resource dependencies for a {fullname(self.__class__)} must be ResourceEnvironmentsGenerators, but the '{k}' resource dependency was instead a {fullname(v.__class__)}"
                )

        remaining_generators = generators.copy()
        self._generators = []
        if specification.environments_sequence:
            for resource_id in specification.environments_sequence:
                if resource_id in remaining_generators:
                    self._generators.append(remaining_generators.pop(resource_id))

        for generator in remaining_generators.values():
            self._generators.append(generator)

    def get_environments(self) -> Iterator[dict[ResourceID, Resource]]:
        for generator in self._generators:
            yield from generator.get_environments()
