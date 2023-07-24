from implicitdict import ImplicitDict
from monitoring.monitorlib.geo import LatLngBoundingBox

from monitoring.uss_qualifier.resources.resource import Resource


class ServiceAreaSpecification(ImplicitDict):
    base_url: str
    """Base URL to use for the Identification Service Area.

    Note that this is the API base URL, not the flights URL (as specified in F3411-19).

    This URL will probably not identify a real resource in tests."""

    footprint: LatLngBoundingBox
    """2D outline of service area"""

    altitude_min: float = 0
    """Lower altitude bound of service area, meters above WGS84 ellipsoid"""

    altitude_max: float = 3048
    """Upper altitude bound of service area, meters above WGS84 ellipsoid"""


class ServiceAreaResource(Resource[ServiceAreaSpecification]):
    specification: ServiceAreaSpecification

    def __init__(self, specification: ServiceAreaSpecification):
        self.specification = specification
