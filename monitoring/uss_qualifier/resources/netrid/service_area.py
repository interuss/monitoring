import datetime
from typing import List, Dict, Any

from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.monitorlib.geo import LatLngPoint
from monitoring.uss_qualifier.resources.resource import Resource


class ServiceAreaSpecification(ImplicitDict):
    base_url: str
    """Base URL to use for the Identification Service Area.

    Note that this is the API base URL, not the flights URL (as specified in F3411-19).

    This URL will probably not identify a real resource in tests."""

    footprint: List[LatLngPoint]
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

    def shifted_time_start(
        self, new_reference_time: datetime.datetime
    ) -> datetime.datetime:
        dt = new_reference_time - self.reference_time.datetime
        return self.time_start.datetime + dt

    def shifted_time_end(
        self, new_reference_time: datetime.datetime
    ) -> datetime.datetime:
        dt = new_reference_time - self.reference_time.datetime
        return self.time_end.datetime + dt

    def get_new_subscription_params(
        self, sub_id: str, start_time: datetime.datetime, duration: datetime.timedelta
    ) -> Dict[str, Any]:
        """
        Builds a dict of parameters that can be used to create a subscription, using this ISA's parameters
        and the passed start time and duration
        """
        return dict(
            sub_id=sub_id,
            area_vertices=[vertex.as_s2sphere() for vertex in self.footprint],
            alt_lo=self.altitude_min,
            alt_hi=self.altitude_max,
            start_time=start_time,
            end_time=start_time + duration,
            uss_base_url=self.base_url,
        )


class ServiceAreaResource(Resource[ServiceAreaSpecification]):
    specification: ServiceAreaSpecification

    def __init__(self, specification: ServiceAreaSpecification):
        self.specification = specification
