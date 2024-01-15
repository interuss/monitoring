import datetime
from typing import List, Dict, Any, Optional

from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.astm.f3548.v21.api import Volume4D

from monitoring.monitorlib.geo import LatLngPoint, make_latlng_rect, Volume3D, Polygon
from monitoring.uss_qualifier.resources.resource import Resource


class USSAreaSpecification(ImplicitDict):
    """Specifies an area and USS related information to create test resources that require them."""

    base_url: str
    """Base URL for the USS

    Note that this is the API base URL, not the flights or any other specific URL.

    This URL will probably not identify a real resource in tests."""

    footprint: List[LatLngPoint]
    """2D outline of service area"""

    altitude_min: float = 0
    """Lower altitude bound of service area, meters above WGS84 ellipsoid"""

    altitude_max: float = 3048
    """Upper altitude bound of service area, meters above WGS84 ellipsoid"""

    def get_new_subscription_params(
        self,
        subscription_id: str,
        start_time: datetime.datetime,
        duration: datetime.timedelta,
        notify_for_op_intents: bool,
        notify_for_constraints: bool,
    ) -> Dict[str, Any]:
        """
        Builds a dict of parameters that can be used to create a subscription, using this ISA's parameters
        and the passed start time and duration
        """
        return dict(
            sub_id=subscription_id,
            area_vertices=make_latlng_rect(
                Volume3D(outline_polygon=Polygon(vertices=self.footprint))
            ),
            min_alt_m=self.altitude_min,
            max_alt_m=self.altitude_max,
            start_time=start_time,
            end_time=start_time + duration,
            base_url=self.base_url,
            notify_for_op_intents=notify_for_op_intents,
            notify_for_constraints=notify_for_constraints,
        )


class USSAreaResource(Resource[USSAreaSpecification]):
    specification: USSAreaSpecification

    def __init__(self, specification: USSAreaSpecification):
        self.specification = specification
