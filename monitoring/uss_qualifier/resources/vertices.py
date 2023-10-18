from typing import List

from implicitdict import ImplicitDict

from monitoring.monitorlib.geo import LatLngPoint
from monitoring.uss_qualifier.resources.resource import Resource


class VerticesSpecification(ImplicitDict):
    """Specifies a list of vertices representing a 2D area.
    Useful for passing arbitrary areas to test scenarios."""

    vertices: List[LatLngPoint]
    """Represents a 2D area"""


class VerticesResource(Resource[VerticesSpecification]):
    specification: VerticesSpecification

    def __init__(self, specification: VerticesSpecification):
        self.specification = specification
