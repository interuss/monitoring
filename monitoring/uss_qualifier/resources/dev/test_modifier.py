from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.resource import (
    Resource,
    ResourceModifyingResource,
)


class TestNumberGeneratorSpecification(ImplicitDict):
    base_id: int


class TestNumberGeneratorResource(Resource[TestNumberGeneratorSpecification]):
    """A simple resource returing 10 numbers, starting from base_id. Used for unit tests."""

    _spec: TestNumberGeneratorSpecification

    def __init__(
        self,
        specification: TestNumberGeneratorSpecification,
        resource_origin: str,
    ):
        super().__init__(specification, resource_origin)
        self._spec = specification

    def build_ids(self) -> list[int]:
        return list(range(self._spec.base_id, self._spec.base_id + 10))


class TestNumberGeneratorModifierSpecification(ImplicitDict):
    shift_interval: int


class TestNumberGeneratorModifierResource(
    ResourceModifyingResource[
        TestNumberGeneratorModifierSpecification, int, TestNumberGeneratorResource
    ]
):
    """Modifier for a TestNumberGeneratorResource. Used for unit tests."""

    def modify(self, key: int) -> TestNumberGeneratorResource:

        # 'Clone' the resource with new specs
        return TestNumberGeneratorResource(
            TestNumberGeneratorSpecification(
                base_id=self.base_resource._spec.base_id
                + self._spec.shift_interval * key,
            ),
            resource_origin=self._modified_resource_origin(str(key)),
        )
