import datetime
from typing import List

from implicitdict import ImplicitDict, StringBasedDateTime
from monitoring.monitorlib.geo import LatLngVertex

from monitoring.uss_qualifier.resources.resource import Resource


class ServiceAreaSpecification(ImplicitDict):
    base_url: str
    """Base URL to use for the Identification Service Area.

    Note that this is the API base URL, not the flights URL (as specified in F3411-19).

    This URL will probably not identify a real resource in tests."""

    footprint: List[LatLngVertex]
    """2D outline of service area"""

    altitude_min: float = 0
    """Lower altitude bound of service area, meters above WGS84 ellipsoid"""

    altitude_max: float = 3048
    """Upper altitude bound of service area, meters above WGS84 ellipsoid"""

    reference_time: StringBasedDateTime
    """Reference time used to adjust start and end times at runtime"""

    time_start: StringBasedDateTime
    """Start time of service area (relative to reference_time)"""

    time_end: StringBasedDateTime
    """End time of service area (relative to reference_time)"""

    def shifted_time_start(self, now: datetime.datetime) -> datetime.datetime:
        dt = now - self.reference_time.datetime
        return self.time_start.datetime + dt

    def shifted_time_end(self, now: datetime.datetime) -> datetime.datetime:
        dt = now - self.reference_time.datetime
        return self.time_end.datetime + dt


class ServiceAreaResource(Resource[ServiceAreaSpecification]):
    specification: ServiceAreaSpecification

    def __init__(self, specification: ServiceAreaSpecification):
        self.specification = specification
