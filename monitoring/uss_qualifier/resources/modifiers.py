from abc import ABC, abstractmethod
from math import isqrt
from typing import Self

from implicitdict import ImplicitDict

from monitoring.monitorlib.geo import LatLngBoundingBox, flatten
from monitoring.uss_qualifier.resources.resource import ResourceModifier


class GeospatialResource(ABC):
    @abstractmethod
    def get_extents(self) -> LatLngBoundingBox:
        pass

    @abstractmethod
    def move(self, meters_east: float, meters_north: float) -> Self:
        pass


class GeospatialModifierSpecification(ImplicitDict):
    meters_east_margin: float = 1000
    meters_north_margin: float = 1000


class GeospatialModifier[GeospatialResourceType: GeospatialResource](
    ResourceModifier[GeospatialModifierSpecification, GeospatialResourceType]
):
    def adjust(self, index: int) -> GeospatialResourceType:
        # Make a grid based on index:
        #      x ->
        # y  0 1 3 6
        # |  2 4 7
        # v  5 8
        #    9
        k = (isqrt(1 + 8 * index) - 1) // 2
        offset = index - k * (k + 1) // 2
        x = k - offset
        y = offset

        rect = self.base_resource.get_extents().to_latlngrect()
        width_m, height_m = flatten(rect.lo(), rect.hi())
        width_m += self._spec.meters_east_margin
        height_m += self._spec.meters_north_margin
        return self.base_resource.move(x * width_m, y * height_m)
