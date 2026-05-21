from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.resource import (
    Resource,
    ResourceModifyingResource,
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
    ResourceModifyingResource[
        NumberGeneratorModifierSpecification, int, NumberGeneratorResource
    ]
):
    """Modifier for a NumberGeneratorResource. Used for unit tests."""

    def provide_resource_for(self, key: int) -> NumberGeneratorResource:

        # 'Clone' the resource with new specs
        return NumberGeneratorResource(
            NumberGeneratorSpecification(
                base_id=self.base_resource._spec.base_id
                + self._spec.shift_interval * key,
            ),
            resource_origin=self._modified_resource_origin(str(key)),
        )
