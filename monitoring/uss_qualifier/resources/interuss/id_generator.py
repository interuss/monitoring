from implicitdict import ImplicitDict

from monitoring.prober.infrastructure import IDFactory
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.resource import (
    Resource,
    ResourceProvidingResource,
    SupportedKeysNotSpecifiedError,
)


class IDGeneratorSpecification(ImplicitDict):
    instance_index: int = 0
    """Namespace for this invocation, from 0 to 255.  Zero preserves legacy IDs."""


class IDGeneratorResource(Resource[IDGeneratorSpecification]):
    _client_identity: ClientIdentityResource
    _instance_index: int
    _id_factory: IDFactory | None

    def __init__(
        self,
        specification: IDGeneratorSpecification,
        resource_origin: str,
        client_identity: ClientIdentityResource,
    ):
        super().__init__(specification, resource_origin)
        IDFactory.validate_instance_index(specification.instance_index)
        self._client_identity = client_identity
        self._instance_index = specification.instance_index
        self._id_factory = None

    @property
    def instance_index(self) -> int:
        return self._instance_index

    def with_instance_index(
        self, instance_index: int, resource_origin: str | None = None
    ) -> "IDGeneratorResource":
        """Derive an independent generator, replacing rather than adding an index."""
        return IDGeneratorResource(
            specification=IDGeneratorSpecification(instance_index=instance_index),
            resource_origin=(resource_origin or f"Instance index {instance_index}")
            + f" derived from {self.resource_origin}",
            client_identity=self._client_identity,
        )

    @property
    def id_factory(self) -> IDFactory:
        # Not thread safe, but the consequences here are acceptable
        if self._id_factory is None:
            self._id_factory = IDFactory(
                self._client_identity.subject(), self.instance_index
            )

        return self._id_factory


class IDGeneratorProviderSpecification(ImplicitDict):
    first_instance_index: int = 1
    """First allocated instance index; environment index i uses first_instance_index + i.

    Allocated indices must fit in 0..255.  Independent providers used concurrently
    with the same client identity must be configured with disjoint ranges.
    """


class IDGeneratorProviderResource(
    ResourceProvidingResource[IDGeneratorProviderSpecification, IDGeneratorResource]
):
    """Provide deterministic ID namespaces for enumerated resource environments."""

    base_resource: IDGeneratorResource
    _first_instance_index: int

    def __init__(
        self,
        specification: IDGeneratorProviderSpecification,
        resource_origin: str,
        base_resource: IDGeneratorResource,
    ):
        super().__init__(specification, resource_origin)
        IDFactory.validate_instance_index(specification.first_instance_index)
        self.base_resource = base_resource
        self._first_instance_index = specification.first_instance_index

    def provide_resource_for(self, **kwargs) -> IDGeneratorResource:
        index = kwargs.get("index")
        if type(index) is not int or index < 0:
            raise SupportedKeysNotSpecifiedError("index must be a nonnegative integer")
        instance_index = self._first_instance_index + index
        return self.base_resource.with_instance_index(
            instance_index,
            resource_origin=self._provided_resource_origin(
                f"index {index} (instance index {instance_index})"
            ),
        )
