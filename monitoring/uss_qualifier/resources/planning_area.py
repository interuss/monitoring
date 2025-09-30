import datetime

from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21.api import (
    EntityID,
    EntityOVN,
    ImplicitSubscriptionParameters,
    OperationalIntentState,
    PutConstraintReferenceParameters,
    PutOperationalIntentReferenceParameters,
    UssBaseURL,
)

from monitoring.monitorlib.geo import make_latlng_rect
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.subscription_params import SubscriptionParams
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.uss_qualifier.resources.volume import VolumeResource


class PlanningAreaSpecification(ImplicitDict):
    base_url: str | None
    """Base URL for the USS

    Note that this is the base URL for the F3548-21 USS API, not the flights or any other specific URL.

    This URL will probably not identify a real resource in tests.

    If not specified, a fake URL will be generated at runtime according to the test in which the resource is being
    used."""

    def get_base_url(self, frames_above: int = 1):
        if "base_url" in self and self.base_url is not None:
            return self.base_url
        return make_fake_url(frames_above=frames_above + 1)


class PlanningAreaResource(Resource[PlanningAreaSpecification]):
    specification: PlanningAreaSpecification
    _volume: VolumeResource

    def __init__(
        self,
        specification: PlanningAreaSpecification,
        volume: VolumeResource,
        resource_origin: str,
    ):
        super().__init__(specification, resource_origin)
        self.specification = specification
        self._volume = volume

    def resolved_volume4d(self, times: dict[TimeDuringTest, Time]) -> Volume4D:
        return self._volume.specification.template.resolve(times)

    def resolved_volume4d_with_times(
        self, time_start: datetime.datetime | None, time_end: datetime.datetime | None
    ) -> Volume4D:
        """resolves this resource to a Volume4D via #resolved_volume4d(), but overrides the time_start and time_end with the provided values"""
        # TODO #1053 we may want to migrate all callers to using resolved_volume4d() with a proper 'times' dict and relevant
        # scenario configurations instead of passing explicit times.
        # Alternatively we could fill in the times map here with all possible options defined
        # to ensure resolution works correctly, and then override the times anyway.
        return Volume4D(
            volume=self.resolved_volume4d({}).volume,
            time_start=Time(time_start) if time_start else None,
            time_end=Time(time_end) if time_end else None,
        )

    def get_new_subscription_params(
        self,
        subscription_id: str,
        start_time: datetime.datetime,
        duration: datetime.timedelta,
        notify_for_op_intents: bool,
        notify_for_constraints: bool,
    ) -> SubscriptionParams:
        """
        Builds a dict of parameters that can be used to create a subscription, using this ISA's parameters
        and the passed start time and duration
        """
        v4d = self.resolved_volume4d_with_times(start_time, start_time + duration)
        return SubscriptionParams(
            sub_id=subscription_id,
            area_vertices=make_latlng_rect(v4d.volume),
            min_alt_m=(
                None
                if v4d.volume.altitude_lower is None
                else v4d.volume.altitude_lower_wgs84_m()
            ),
            max_alt_m=(
                None
                if v4d.volume.altitude_upper is None
                else v4d.volume.altitude_upper_wgs84_m()
            ),
            start_time=start_time,
            end_time=start_time + duration,
            base_url=self.specification.get_base_url(frames_above=2),
            notify_for_op_intents=notify_for_op_intents,
            notify_for_constraints=notify_for_constraints,
        )

    def get_new_operational_intent_ref_params(
        self,
        key: list[EntityOVN],
        state: OperationalIntentState,
        uss_base_url: UssBaseURL,
        time_start: datetime.datetime,
        time_end: datetime.datetime,
        subscription_id: EntityID | None,
        implicit_sub_base_url: UssBaseURL | None = None,
        implicit_sub_for_constraints: bool | None = None,
    ) -> PutOperationalIntentReferenceParameters:
        """
        Builds a PutOperationalIntentReferenceParameters object that can be used against the DSS OIR API.

        The extents contained in these parameters contain a single 4DVolume, which may not be entirely realistic,
        but is sufficient in situations where the content of the OIR is irrelevant as long as it is valid, such
        as for testing authentication or parameter validation.

        Note that this method allows building inconsistent parameters:
        """
        return PutOperationalIntentReferenceParameters(
            extents=[
                self.resolved_volume4d_with_times(time_start, time_end).to_f3548v21()
            ],
            key=key,
            state=state,
            uss_base_url=uss_base_url,
            subscription_id=subscription_id,
            new_subscription=(
                ImplicitSubscriptionParameters(
                    uss_base_url=implicit_sub_base_url,
                    notify_for_constraints=implicit_sub_for_constraints,
                )
                if implicit_sub_base_url
                else None
            ),
        )

    def get_new_constraint_ref_params(
        self,
        time_start: datetime.datetime,
        time_end: datetime.datetime,
    ) -> PutConstraintReferenceParameters:
        """
        Builds a PutConstraintReferenceParameters object that can be used against the DSS OCR API.

        The extents contained in these parameters contain a single 4DVolume, which may not be entirely realistic,
        but is sufficient in situations where the content of the CR is irrelevant as long as it is valid, such
        as for testing authentication or parameter validation.
        """
        return PutConstraintReferenceParameters(
            extents=[
                self.resolved_volume4d_with_times(time_start, time_end).to_f3548v21()
            ],
            uss_base_url=self.specification.get_base_url(frames_above=2),
        )
