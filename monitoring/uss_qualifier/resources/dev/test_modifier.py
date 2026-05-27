from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.resource import (
    Resource,
    ResourceProvidingResource,
    SupportedKeysNotSpecifiedError,
)


class NumberGeneratorSpecification(ImplicitDict):
    base_id: int


class NumberGeneratorResource(Resource[NumberGeneratorSpecification]):
    """A simple resource returing 10 numbers, starting from base_id. Used for unit tests."""

    _spec: NumberGeneratorSpecification

    def __init__(
        self,
        specification: NumberGeneratorSpecification,
        resource_origin: str,
    ):
        super().__init__(specification, resource_origin)
        self._spec = specification

    def build_ids(self) -> list[int]:
        return list(range(self._spec.base_id, self._spec.base_id + 10))


class NumberGeneratorModifierSpecification(ImplicitDict):
    shift_interval: int


class NumberGeneratorModifierResource(
    ResourceProvidingResource[
        NumberGeneratorModifierSpecification, NumberGeneratorResource
    ]
):
    """Modifier for a NumberGeneratorResource. Used for unit tests."""

    _spec: NumberGeneratorModifierSpecification
    base_resource: NumberGeneratorResource

    def __init__(
        self,
        specification: NumberGeneratorModifierSpecification,
        resource_origin: str,
        base_resource: NumberGeneratorResource,
    ):
        super().__init__(specification, resource_origin)
        self._spec = specification
        self.base_resource = base_resource

    def _modified_resource_origin(self, index: int) -> str:
        return f"Modification {index} of {self.base_resource.resource_origin} by {self.resource_origin}"

    def provide_resource_for(self, **kwargs) -> NumberGeneratorResource:
        if "index" not in kwargs:
            raise SupportedKeysNotSpecifiedError("index not specified")
        index = kwargs["index"]
        if not isinstance(index, int):
            raise SupportedKeysNotSpecifiedError("index is not an int")

        # 'Clone' the base resource with new specs
        return NumberGeneratorResource(
            NumberGeneratorSpecification(
                base_id=self.base_resource._spec.base_id
                + self._spec.shift_interval * index,
            ),
            resource_origin=self._modified_resource_origin(index),
        )
