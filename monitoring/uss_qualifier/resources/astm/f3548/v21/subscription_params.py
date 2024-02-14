import datetime
from typing import List, Optional, Self

from implicitdict import ImplicitDict

from monitoring.monitorlib.geo import LatLngPoint


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

    start_time: datetime.datetime
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
