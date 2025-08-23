import s2sphere
from implicitdict import ImplicitDict

from monitoring.monitorlib.geo import (
    Volume3D,
    get_latlngrect_vertices,
    make_latlng_rect,
)
from monitoring.monitorlib.geotemporal import Volume4DTemplate
from monitoring.uss_qualifier.resources.resource import Resource


class VolumeSpecification(ImplicitDict):
    """Specifies a volume in time and three-dimensional space.
    The time-bounds, as well as the lower and upper bounds of the Volume3D may be omitted if a timeless and altitude-free two-dimensional area is required.
    See monitoring.monitorlib.geotemporal.Volume4DTemplate for details.
    """

    template: Volume4DTemplate

    def vertices(self) -> list[s2sphere.LatLng]:
        """Returns the vertices of the 2D area represented by this volume specification. If the underlying volume is a Polygon, its
        original vertices are returned. If it is a Circle, the vertices of the bounding rectangle are returned.
        """
        if (
            self.template.outline_polygon is not None
            and self.template.outline_polygon.vertices is not None
        ):
            return [v.as_s2sphere() for v in self.template.outline_polygon.vertices]
        else:
            return get_latlngrect_vertices(
                make_latlng_rect(Volume3D(outline_circle=self.template.outline_circle))
            )


class VolumeResource(Resource[VolumeSpecification]):
    specification: VolumeSpecification

    def __init__(self, specification: VolumeSpecification, resource_origin: str):
        super().__init__(specification, resource_origin)
        self.specification = specification
