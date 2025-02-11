import datetime
from typing import List, Optional

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

from monitoring.monitorlib.geo import Volume3D, make_latlng_rect
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.temporal import Time
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources.astm.f3548.v21.subscription_params import (
    SubscriptionParams,
)
from monitoring.uss_qualifier.resources.resource import Resource


class PlanningAreaSpecification(ImplicitDict):
    """Specifies an area and USS related information to create test resources that require them."""

    base_url: Optional[str]
    """Base URL for the USS

    Note that this is the base URL for the F3548-21 USS API, not the flights or any other specific URL.

    This URL will probably not identify a real resource in tests.

    If not specified, a fake URL will be generated at runtime according to the test in which the resource is being
    used."""

    volume: Volume3D
    """3D volume of service area"""

    def get_volume4d(
        self, time_start: datetime.datetime, time_end: datetime.datetime
    ) -> Volume4D:
        return Volume4D(
            volume=self.volume,
            time_start=Time(time_start),
            time_end=Time(time_end),
        )

    def get_base_url(self, frames_above: int = 1):
        if "base_url" in self and self.base_url is not None:
            return self.base_url
        return make_fake_url(frames_above=frames_above + 1)

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
        return SubscriptionParams(
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
            base_url=self.get_base_url(frames_above=2),
            notify_for_op_intents=notify_for_op_intents,
            notify_for_constraints=notify_for_constraints,
        )

    def get_new_operational_intent_ref_params(
        self,
        key: List[EntityOVN],
        state: OperationalIntentState,
        uss_base_url: UssBaseURL,
        time_start: datetime.datetime,
        time_end: datetime.datetime,
        subscription_id: Optional[EntityID],
        implicit_sub_base_url: Optional[UssBaseURL] = None,
        implicit_sub_for_constraints: Optional[bool] = None,
    ) -> PutOperationalIntentReferenceParameters:
        """
        Builds a PutOperationalIntentReferenceParameters object that can be used against the DSS OIR API.

        The extents contained in these parameters contain a single 4DVolume, which may not be entirely realistic,
        but is sufficient in situations where the content of the OIR is irrelevant as long as it is valid, such
        as for testing authentication or parameter validation.

        Note that this method allows building inconsistent parameters:
        """
        return PutOperationalIntentReferenceParameters(
            extents=[self.get_volume4d(time_start, time_end).to_f3548v21()],
            key=key,
            state=state,
            uss_base_url=uss_base_url,
            subscription_id=subscription_id,
            new_subscription=ImplicitSubscriptionParameters(
                uss_base_url=implicit_sub_base_url,
                notify_for_constraints=implicit_sub_for_constraints,
            )
            if implicit_sub_base_url
            else None,
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
            extents=[self.get_volume4d(time_start, time_end).to_f3548v21()],
            uss_base_url=self.get_base_url(frames_above=2),
        )


class PlanningAreaResource(Resource[PlanningAreaSpecification]):
    specification: PlanningAreaSpecification

    def __init__(self, specification: PlanningAreaSpecification, resource_origin: str):
        super(PlanningAreaResource, self).__init__(specification, resource_origin)
        self.specification = specification
