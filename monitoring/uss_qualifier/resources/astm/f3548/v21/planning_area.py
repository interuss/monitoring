import datetime
from typing import List, Dict, Any, Optional

from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.astm.f3548.v21.api import Volume4D

from monitoring.monitorlib.geo import LatLngPoint, make_latlng_rect, Volume3D, Polygon
from monitoring.uss_qualifier.resources.resource import Resource


class PlanningAreaSpecification(ImplicitDict):
    """Specifies an area and USS related information to create test resources that require them."""

    base_url: str
    """Base URL for the USS

    Note that this is the base URL for the F3548-21 USS API, not the flights or any other specific URL.

    This URL will probably not identify a real resource in tests."""

    volume: Volume3D
    """3D volume of service area"""

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
            area_vertices=make_latlng_rect(self.volume),
            min_alt_m=None
            if self.volume.altitude_lower is None
            else self.volume.altitude_lower_wgs84_m(),
            max_alt_m=None
            if self.volume.altitude_upper is None
            else self.volume.altitude_upper_wgs84_m(),
            start_time=start_time,
            end_time=start_time + duration,
            base_url=self.base_url,
            notify_for_op_intents=notify_for_op_intents,
            notify_for_constraints=notify_for_constraints,
        )


class PlanningAreaResource(Resource[PlanningAreaSpecification]):
    specification: PlanningAreaSpecification

    def __init__(self, specification: PlanningAreaSpecification):
        self.specification = specification
