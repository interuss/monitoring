from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.resource import Resource, ResourceModifier


class TestModifierSpecification(ImplicitDict):
    base_id: int


class TestModifierResource(Resource[TestModifierSpecification]):
    """TestModifierResource is a simple resource returing 10 number, starting from base_id. Used for unit tests."""

    _spec: TestModifierSpecification

    def __init__(
        self,
        specification: TestModifierSpecification,
        resource_origin: str,
    ):
        super().__init__(specification, resource_origin)
        self._spec = specification

    def build_ids(self) -> list[int]:
        return list(range(self._spec.base_id, self._spec.base_id + 10))


class TestModifierModifierSpecification(ImplicitDict):
    shift_interval: int


class TestModifierModifierResource(
    ResourceModifier[TestModifierModifierSpecification, TestModifierResource]
):
    """Modifier for a TestModifierResource. Used for unit tests."""

    def adjust(self, index: int) -> TestModifierResource:

        # 'Clone' the resource with new specs
        return TestModifierResource(
            TestModifierSpecification(
                base_id=self.base_resource._spec.base_id
                + self._spec.shift_interval * index,
            ),
            resource_origin=self.base_resource.resource_origin,
        )
