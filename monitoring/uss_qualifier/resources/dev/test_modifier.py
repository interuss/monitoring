from implicitdict import ImplicitDict

from monitoring.monitorlib.geo import LatLngBoundingBox
from monitoring.uss_qualifier.resources.modifiers import (
    GeospatialModifier,
    GeospatialResource,
)
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


class TestSquareSpecification(ImplicitDict):
    lat_center: float
    lng_center: float


class TestSquareResource(Resource[TestSquareSpecification], GeospatialResource):
    """1km x 1km square centered at (lat_center, lng_center). Used for unit tests."""

    SQUARE_SIDE_M = 1000.0

    _spec: TestSquareSpecification

    def __init__(
        self,
        specification: TestSquareSpecification,
        resource_origin: str,
    ):
        super().__init__(specification, resource_origin)
        self._spec = specification

    def get_extents(self) -> LatLngBoundingBox:
        point = LatLngBoundingBox(
            lat_min=self._spec.lat_center,
            lat_max=self._spec.lat_center,
            lng_min=self._spec.lng_center,
            lng_max=self._spec.lng_center,
        )
        return point.expand(
            north_meters=self.SQUARE_SIDE_M / 2,
            east_meters=self.SQUARE_SIDE_M / 2,
            south_meters=self.SQUARE_SIDE_M / 2,
            west_meters=self.SQUARE_SIDE_M / 2,
        )

    def move(self, meters_east: float, meters_north: float) -> "TestSquareResource":
        shifted = self.get_extents().expand(
            north_meters=meters_north,
            east_meters=meters_east,
            south_meters=-meters_north,
            west_meters=-meters_east,
        )
        return TestSquareResource(
            TestSquareSpecification(
                lat_center=(shifted.lat_min + shifted.lat_max) / 2,
                lng_center=(shifted.lng_min + shifted.lng_max) / 2,
            ),
            resource_origin=self.resource_origin,
        )


class TestSquareModifier(GeospatialModifier[TestSquareResource]):
    pass
