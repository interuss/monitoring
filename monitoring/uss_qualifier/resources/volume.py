import s2sphere
from implicitdict import ImplicitDict

from monitoring.monitorlib.geo import (
    LatLngPoint,
)
from monitoring.monitorlib.geotemporal import Volume4DTemplate
from monitoring.uss_qualifier.resources.resource import Resource


class VolumeSpecification(ImplicitDict):
    """Specifies a volume in time and three-dimensional space.
    The time-bounds, as well as the lower and upper bounds of the Volume3D may be omitted if a timeless and altitude-free two-dimensional area is required.
    See monitoring.monitorlib.geotemporal.Volume4DTemplate for details.
    """

    template: Volume4DTemplate

    def s2_vertices(self) -> list[s2sphere.LatLng]:
        """Returns the vertices of the 2D area represented by this volume specification, after application of the template's transformations.
        Note that if the underlying volume contains a Circle, the vertices of its bounding rectangle are returned.
        """
        return self.template.resolve({}).volume.s2_vertices()

    def vertices(self) -> list[LatLngPoint]:
        """Returns the vertices of the 2D area represented by this volume specification, after application of the template's transformations.
        Note that if the underlying volume contains a Circle, the vertices of its bounding rectangle are returned.
        """
        return [LatLngPoint.from_s2(v) for v in self.s2_vertices()]


class VolumeResource(Resource[VolumeSpecification]):
    specification: VolumeSpecification

    def __init__(self, specification: VolumeSpecification, resource_origin: str):
        super().__init__(specification, resource_origin)
        self.specification = specification
