from typing import Optional, List

from implicitdict import ImplicitDict

from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import AuthSpec
from monitoring.monitorlib.rid import RIDVersion

ObservationAreaID = str
"""Unique identifier of observation area."""


class F3411ObservationArea(ImplicitDict):
    """How F3411 activity is being observed."""

    auth_spec: AuthSpec
    """This auth spec is used when performing F3411 observation activities."""

    dss_base_url: str
    """This DSS URL is used when performing relevant F3411 observation activities."""

    rid_version: RIDVersion
    """F3411 observation is performed according to this version of F3411."""

    poll: bool
    """This area observes by periodically polling for information."""

    subscription_id: str
    """The F3411 subscription ID established to provide observation via notifications."""


class F3548ObservationArea(ImplicitDict):
    """How F3548 activity is being observed."""

    auth_spec: AuthSpec
    """This auth spec is used when performing F3548 observation activities."""

    dss_base_url: str
    """This DSS URL is used when performing relevant F3548 observation activities."""

    monitor_op_intents: bool
    """Operational intent activity is being monitored."""

    monitor_constraints: bool
    """Constraint activity is being monitored."""

    poll: bool
    """This area observes by periodically polling for information."""

    subscription_id: Optional[str]
    """The F3548 subscription ID established to provide observation via notifications."""


class ObservationArea(ImplicitDict):
    """An established (or previously-established) observation area."""

    id: ObservationAreaID
    """Unique identifier of observation area"""

    area: Volume4D
    """Spatial-temporal area being observed."""

    f3411: Optional[F3411ObservationArea] = None
    """How F3411 information is being observed (or not observed, if not specified)."""

    f3548: Optional[F3548ObservationArea] = None
    """How F3548 information is being observed (or not observed, if not specified)."""

    @property
    def polls(self) -> bool:
        """Whether any of the observation activity involves periodic polling."""
        return (self.f3411 and self.f3411.poll) or (self.f3548 and self.f3548.poll)


class F3411ObservationAreaRequest(ImplicitDict):
    """How to observe F3411 activity."""

    auth_spec: Optional[AuthSpec] = None
    """If specified, use this auth spec when performing observation activities.

    If not specified or blank, use auth spec provided on the command line."""

    dss_base_url: Optional[str] = None
    """If specified, use the DSS at this base URL when performing relevant observation activities.

    If not specified or blank, use DSS URL provided on the command line."""

    rid_version: RIDVersion
    """Perform observation activities according to this version of F3411."""

    poll: bool = False
    """Observe by periodically polling for information."""

    subscribe: bool = False
    """Observe by establishing a subscription and logging incoming notifications."""


class F3548ObservationAreaRequest(ImplicitDict):
    """How to observe F3548 activity."""

    auth_spec: Optional[AuthSpec] = None
    """If specified, use this auth spec when performing observation activities.

    If not specified or blank, use auth spec provided on the command line."""

    dss_base_url: Optional[str] = None
    """If specified, use the DSS at this base URL when performing relevant observation activities.

    If not specified or blank, use DSS URL provided on the command line."""

    monitor_op_intents: bool = False
    """Indicate interest in operational intents while observing."""

    monitor_constraints: bool = False
    """Indicate interest in constraints while observing."""

    poll: bool = False
    """Observe by periodically polling for information."""

    subscribe: bool = False
    """Observe by establishing a subscription and logging incoming notifications."""


class ObservationAreaRequest(ImplicitDict):
    """Request to create a new observation area."""

    area: Volume4D
    """Spatial-temporal area that should be observed."""

    f3411: Optional[F3411ObservationAreaRequest] = None
    """How to observe F3411 (NetRID) activity."""

    f3548: Optional[F3548ObservationAreaRequest] = None
    """How to observe F3548 (strategic coordination, conformance monitoring, and constraints) activity."""

    @property
    def polls(self) -> bool:
        """Whether any of the observation activity requested involves periodic polling."""
        return (self.f3411 and self.f3411.poll) or (self.f3548 and self.f3548.poll)


class ListObservationAreasResponse(ImplicitDict):
    """Response to list observation areas."""

    areas: List[ObservationArea]
    """Observation areas that exist in the system."""


class PutObservationAreaRequest(ImplicitDict):
    """Response to upsert an observation area."""

    area: ObservationAreaRequest
    """Specifications for the new/updated observation area."""


class ObservationAreaResponse(ImplicitDict):
    """Response to an operation involving a single observation area."""

    area: ObservationArea
    """Resulting observation area."""


class ImportObservationAreasRequest(ImplicitDict):
    """Request payload to import subscriptions as observation areas."""

    area: Volume4D
    """Spatial-temporal area containing subscriptions to be imported."""

    f3411: Optional[RIDVersion] = None
    """If specified, search for subscriptions using this F3411 version."""

    f3548: bool = False
    """If true, search for F3548 subscriptions."""
