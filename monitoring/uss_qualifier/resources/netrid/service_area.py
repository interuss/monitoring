import datetime
from typing import Any

import arrow
from implicitdict import ImplicitDict

from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.temporal import Time, TimeDuringTest
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
            {
                TimeDuringTest.StartOfTestRun: now,
                TimeDuringTest.StartOfScenario: now,
                TimeDuringTest.TimeOfEvaluation: now,
            }
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

    def resolved_volume4d(self, times: dict[TimeDuringTest, Time]) -> Volume4D:
        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        return self._volume.specification.template.resolve(times)

    def resolved_time_bounds(
        self, times: dict[TimeDuringTest, Time]
    ) -> tuple[datetime.datetime, datetime.datetime]:
        v4d = self.resolved_volume4d(times)
        if v4d.time_start is None or v4d.time_end is None:
            # Note this should not happen as we check at construction time that these bounds exist
            raise ValueError("The underlying volume does not have time bounds")
        return v4d.time_start.datetime, v4d.time_end.datetime

    def resolved_altitude_bounds(
        self, times: dict[TimeDuringTest, Time]
    ) -> tuple[float, float]:
        v3d = self.resolved_volume4d(times).volume
        if v3d.altitude_lower is None or v3d.altitude_upper is None:
            # Note this should not happen as we check at construction time that these bounds exist
            raise ValueError("The underlying volume does not have altitude bounds")
        return v3d.altitude_lower.to_w84_m(), v3d.altitude_upper.to_w84_m()

    def get_new_subscription_params(
        self, sub_id: str, start_time: datetime.datetime, duration: datetime.timedelta
    ) -> dict[str, Any]:
        # TODO move to VolumeResource (?) or at least merge with the similar function in PlanningAreaResource
        """
        Builds a dict of parameters that can be used to create a subscription, using this ISA's parameters
        and the passed start time and duration
        """
        alt_lo, alt_hi = self.resolved_altitude_bounds({})
        return dict(
            sub_id=sub_id,
            area_vertices=self.resolved_volume4d({}).volume.s2_vertices(),
            alt_lo=alt_lo,
            alt_hi=alt_hi,
            start_time=start_time,
            end_time=start_time + duration,
            uss_base_url=self.specification.base_url,
        )
