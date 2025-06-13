from __future__ import annotations

import datetime
from typing import List, Optional, Self

import s2sphere
from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21.api import PutSubscriptionParameters

from monitoring.monitorlib.geo import LatLngPoint
from monitoring.monitorlib.mutate import scd as mutate


class SubscriptionParams(ImplicitDict):
    """
    Parameters for creating/mutating a subscription on the DSS in the SCD context
    """

    sub_id: str
    """Uniquely identifies the subscription"""

    area_vertices: List[LatLngPoint]
    """List of vertices of a polygon defining the area of interest"""

    min_alt_m: Optional[float]
    """Minimum altitude in meters"""

    max_alt_m: Optional[float]
    """Maximum altitude in meters"""

    start_time: Optional[datetime.datetime] = None
    """Start time of subscription"""

    end_time: datetime.datetime
    """End time of subscription"""

    base_url: str
    """Base URL for the USS

    Note that this is the base URL for the F3548-21 USS API, not the flights or any other specific URL.

    This URL will probably not identify a real resource in tests."""

    notify_for_op_intents: bool
    """Whether to notify for operational intents"""

    notify_for_constraints: bool
    """Whether to notify for constraints"""

    def copy(self) -> Self:
        return SubscriptionParams(super().copy())

    def to_upsert_subscription_params(
        self, area: s2sphere.LatLngRect
    ) -> PutSubscriptionParameters:
        """
        Prepares the subscription parameters to be used in the body of an HTTP request
        to create or update a subscription on the DSS in the SCD context.

        Args:
            area: area to include in the subscription parameters

        Returns:
            A dict to be passed as the request body when calling the subscription creation or update API.

        """
        return mutate.build_upsert_subscription_params(
            area_vertices=area,
            start_time=self.start_time,
            end_time=self.end_time,
            base_url=self.base_url,
            notify_for_op_intents=self.notify_for_op_intents,
            notify_for_constraints=self.notify_for_constraints,
            min_alt_m=self.min_alt_m,
            max_alt_m=self.max_alt_m,
        )

    def shift_time(self, shift: datetime.timedelta) -> SubscriptionParams:
        """
        Returns a new SubscriptionParams object with the start and end times shifted by the given timedelta.
        """
        return SubscriptionParams(
            sub_id=self.sub_id,
            area_vertices=self.area_vertices,
            min_alt_m=self.min_alt_m,
            max_alt_m=self.max_alt_m,
            start_time=self.start_time + shift if self.start_time else None,
            end_time=self.end_time + shift,
            base_url=self.base_url,
            notify_for_op_intents=self.notify_for_op_intents,
            notify_for_constraints=self.notify_for_constraints,
        )
