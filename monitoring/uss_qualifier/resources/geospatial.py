from abc import ABC, abstractmethod
from math import isqrt
from typing import Self

from implicitdict import ImplicitDict

from monitoring.monitorlib.geo import LatLngBoundingBox, flatten
from monitoring.uss_qualifier.resources.resource import (
    Resource,
    ResourceProvidingResource,
)


class GeospatialResource(Resource, ABC):
    @abstractmethod
    def get_extents(self) -> LatLngBoundingBox:
        pass

    @abstractmethod
    def move(self, meters_east: float, meters_north: float) -> Self:
        """Return a copy of this resource that has been moved the specified number of meters east and north."""
        pass


class TriangularCascadeSoutheastSpecification(ImplicitDict):
    meters_east_margin: float
    """Modify the resource by moving it this far along the east-west axis to separate it from other modification instances."""

    meters_north_margin: float
    """Modify the resource by moving it this far along the north-south axis to separate it from other modification instances."""


class TriangularCascadeSoutheastResource[GeospatialResourceType: GeospatialResource](
    ResourceProvidingResource[
        TriangularCascadeSoutheastSpecification, GeospatialResourceType
    ]
):
    """Provides modified copies of a base geospatial resource which are offset east and south of the original resource."""

    base_resource: GeospatialResourceType

    def __init__(
        self,
        specification: TriangularCascadeSoutheastSpecification,
        resource_origin: str,
        base_resource: GeospatialResourceType,
    ):
        super().__init__(specification, resource_origin)
        self._spec = specification
        self.base_resource = base_resource

    def provide_resource_for(self, **kwargs) -> GeospatialResourceType:

        if "index" not in kwargs:
            raise ValueError("Need an index")

        index = kwargs["index"]
        assert isinstance(index, int)

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
