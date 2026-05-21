import datetime
from typing import Any

import arrow
from implicitdict import ImplicitDict

from monitoring.monitorlib.temporal import TestTimeContext, Time
from monitoring.uss_qualifier.resources import VolumeResource
from monitoring.uss_qualifier.resources.resource import Resource


class ServiceAreaSpecification(ImplicitDict):
    base_url: str
    """Base URL to use for the Identification Service Area.

    Note that this is the API base URL, not the flights URL (as specified in F3411-19).

    This URL will probably not identify a real resource in tests."""


class ServiceAreaResource(Resource[ServiceAreaSpecification]):
    specification: ServiceAreaSpecification
    _volume: VolumeResource

    def __init__(
        self,
        specification: ServiceAreaSpecification,
        resource_origin: str,
        volume: VolumeResource,
    ):
        super().__init__(specification, resource_origin)
        self.specification = specification
        self._volume = volume

        now = Time(arrow.utcnow().datetime)
        resolved_for_tests = self._volume.specification.template.resolve(
            TestTimeContext.all_times_are(now)
        )

        if (
            resolved_for_tests.volume.altitude_lower is None
            or resolved_for_tests.volume.altitude_upper is None
        ):
            raise ValueError(
                f"In order to be usable for a ServiceAreaResource, the provided VolumeResource must declare altitude bounds. The volume template was obtained from: {resource_origin}"
            )

        if resolved_for_tests.time_start is None or resolved_for_tests.time_end is None:
            raise ValueError(
                f"In order to be usable for a ServiceAreaResource, the provided VolumeResource must declare time bounds. The volume template was obtained from: {resource_origin}"
            )

    def s2_vertices(self):
        return self._volume.specification.s2_vertices()

    @property
    def altitude_min(self) -> float:
        """Lower altitude bound of service area, meters above WGS84 ellipsoid"""
        v3d = self._volume.specification.template.resolve_3d()
        if v3d.altitude_lower is None:
            # Note this should not happen as we check at construction time that this bound exists
            raise ValueError(
                "The underlying volume does not have a lower altitude bound"
            )
        return v3d.altitude_lower.to_w84_m()

    @property
    def altitude_max(self) -> float:
        """Upper altitude bound of service area, meters above WGS84 ellipsoid"""
        v3d = self._volume.specification.template.resolve_3d()
        if v3d.altitude_upper is None:
            # Note this should not happen as we check at construction time that this bound exists
            raise ValueError(
                "The underlying volume does not have a lower altitude bound"
            )
        return v3d.altitude_upper.to_w84_m()

    def resolved_time_bounds(
        self, context: TestTimeContext
    ) -> tuple[datetime.datetime, datetime.datetime]:
        time_start, time_end = self._volume.specification.template.resolve_times(
            context
        )
        if time_start is None or time_end is None:
            # Note this should not happen as we check at construction time that these bounds exist
            raise ValueError("The underlying volume does not have time bounds")
        return time_start.datetime, time_end.datetime

    @property
    def base_url(self) -> str:
        return self.specification.base_url

    def get_new_subscription_params(
        self, sub_id: str, start_time: datetime.datetime, duration: datetime.timedelta
    ) -> dict[str, Any]:
        """
        Builds a dict of parameters that can be used to create a subscription, using this ISA's parameters
        and the passed start time and duration
        """
        return dict(
            sub_id=sub_id,
            area_vertices=self.s2_vertices(),
            alt_lo=self.altitude_min,
            alt_hi=self.altitude_max,
            start_time=start_time,
            end_time=start_time + duration,
            uss_base_url=self.base_url,
        )
