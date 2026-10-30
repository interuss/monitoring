from typing import Optional

from implicitdict import ImplicitDict, StringBasedDateTime, StringBasedTimeDelta

from monitoring.benchmarker.configurations.user.astm import scd
from monitoring.benchmarker.configurations.user.astm.dss import ASTMDSSSelectionStrategy
from monitoring.monitorlib.geo import Altitude, LatLngBoundingBox, LatLngPoint
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.definitions import ResourceID


class BenchmarkUserName(str):
    """Unique (within benchmark configuration) name for a means to generate load."""


class FixedLocationSpecification(ImplicitDict):
    horizontal: LatLngPoint
    vertical: Altitude


class RandomLocationSpecification(ImplicitDict):
    uniform_box: LatLngBoundingBox
    """Selected flight location will be drawn uniformly from this box."""

    vertical: Altitude
    """Selected flight location will be at exactly this altitude."""


class FlightTimeGenerationSpecification(ImplicitDict):
    fixed_spacing: Optional[StringBasedTimeDelta]
    """Add this fixed delay between the end of the previous flight and the start of the next flight."""

    uniform_random_spacing: Optional[StringBasedTimeDelta]
    """Add a random delay uniformly distributed between 0 and this duration between the end of the previous flight and the start of the next flight."""


class FlightLocationGenerationSpecification(ImplicitDict):
    fixed_location: Optional[FixedLocationSpecification]
    """Always choose the same flight location."""

    random_location: Optional[RandomLocationSpecification]
    """Choose a flight location at random."""


class FixedVolumesSpecification(ImplicitDict):
    origin_horizontal: LatLngPoint
    origin_vertical: Altitude
    origin_time: StringBasedDateTime
    volumes: list[Volume4D]


class FlightShapeGenerationSpecification(ImplicitDict):
    fixed_volumes: Optional[FixedVolumesSpecification]


class IndependentComponentsFlightGenerationSpecification(ImplicitDict):
    time: FlightTimeGenerationSpecification
    """Means to generate the start times of flights."""

    location: FlightLocationGenerationSpecification
    """Means to generate flight locations."""

    shape: FlightShapeGenerationSpecification
    """Means to generate flight shapes.

    Note that these volumes represent planned volumes and the flight may be ended before the end of the volumes."""


class FlightExecutionSpecification(ImplicitDict):
    end_flight_before_end: Optional[StringBasedTimeDelta]
    """If specified, the operator ends their flight early this amount of time before the flight is scheduled to end."""

    end_flight_after_start: Optional[StringBasedTimeDelta]
    """If specified, the operator ends their flight early this amount of time after the flight began."""


class FlightGenerationSpecification(ImplicitDict):
    independent_time_location_shape: Optional[
        IndependentComponentsFlightGenerationSpecification
    ]
    """The time, location, and shape of flights are generated independently."""

    execution: Optional[FlightExecutionSpecification]
    """How operator actually executes their planned flights."""


class ASTMNetRIDISAPerFlightStrategySpecification(ImplicitDict):
    """Create an ISA per flight."""

    before_flight_start: StringBasedTimeDelta
    """Create the ISA this amount of time before the start of the flight."""

    after_flight_end: Optional[StringBasedTimeDelta]
    """Delete the ISA this amount of time after the end of this flight."""


class ASTMNetRIDISAStrategySpecification(ImplicitDict):
    """Strategy used to ensure at least one ISA covers every flight."""

    isa_per_flight: Optional[ASTMNetRIDISAPerFlightStrategySpecification]


class ASTMNetRIDBehaviorSpecification(ImplicitDict):
    rid_version: RIDVersion

    dss_pool: list[ResourceID]
    """Means to interact with the ASTM DSS.

    Benchmark configuration must contain a `resources.astm.f3411.DSSInstanceResource` resource with each of these names."""

    dss_selection_strategy: Optional[ASTMDSSSelectionStrategy]

    isa_strategy: ASTMNetRIDISAStrategySpecification


class FlightPlannerSpecification(ImplicitDict):
    """User planning flights coordinated via UTM standards."""

    flight_generation: FlightGenerationSpecification
    """How flight planner generates their flights."""

    astm_netrid_behavior: Optional[ASTMNetRIDBehaviorSpecification]
    """How flight planner provides ASTM NetRID service for their flights."""

    scd_behavior: Optional[scd.BehaviorSpecification]
    """How flight planner provides strategic conflict detection service for their flights."""


class NetRIDObserverBehaviorSpecification(ImplicitDict):
    """How each virtual observer served by a NetRID display provider behaves."""

    area: LatLngBoundingBox
    """The center of each observation is drawn uniformly at random within this area."""

    view_lat_size: float
    """Height, in degrees of latitude, of the rectangle observed (centered on the observation center)."""

    view_lng_size: float
    """Width, in degrees of longitude, of the rectangle observed (centered on the observation center)."""

    min_observation_duration: StringBasedTimeDelta
    """Duration of each observation is drawn uniformly at random between this value and max_observation_duration."""

    max_observation_duration: StringBasedTimeDelta
    """Duration of each observation is drawn uniformly at random between min_observation_duration and this value."""

    query_interval: StringBasedTimeDelta
    """While observing, the observer queries its display provider for flights in its observed rectangle this often."""

    mean_time_between_observations: StringBasedTimeDelta
    """Time between the end of an observation and the start of the observer's next observation is exponentially distributed with this mean."""


class NetRIDDisplayProviderSubscriptionStrategySpecification(ImplicitDict):
    """How a NetRID display provider establishes subscriptions to serve its observers."""

    s2_level: int
    """The display provider maintains one subscription per S2 cell at this level, for each cell covering an area queried by an observer."""

    min_alt: Altitude
    """Altitude below which subscriptions do not apply."""

    max_alt: Altitude
    """Altitude above which subscriptions do not apply."""

    initial_duration: StringBasedTimeDelta
    """When an observer query covers a cell without an unexpired subscription, a subscription is created for that cell with this duration."""

    extension_window: StringBasedTimeDelta
    """When an observer query covers a cell whose subscription expires in less than this amount of time, the subscription is extended."""

    extension_duration: StringBasedTimeDelta
    """Amount of time by which the end of a subscription is pushed back when it is extended."""

    delete_after_unused: Optional[StringBasedTimeDelta]
    """If specified, a subscription is deleted when no observer query has covered its cell for this amount of time.  Otherwise, subscriptions are left to expire."""


class NetRIDDisplayProviderSpecification(ImplicitDict):
    """User acting as a NetRID display provider serving virtual observers."""

    dss_pool: list[ResourceID]
    """Means to interact with the ASTM DSS.

    Benchmark configuration must contain a `resources.astm.f3411.DSSInstanceResource` resource with each of these names."""

    dss_selection_strategy: Optional[ASTMDSSSelectionStrategy]

    observers: int
    """Number of virtual observers served by this display provider."""

    observer_behavior: NetRIDObserverBehaviorSpecification
    """How each of the virtual observers behaves."""

    subscription_strategy: NetRIDDisplayProviderSubscriptionStrategySpecification
    """How the display provider establishes subscriptions to serve its observers."""


class BenchmarkUserSpecification(ImplicitDict):
    name: BenchmarkUserName

    flight_planner: Optional[FlightPlannerSpecification]
    """User is a USS client that plans flights coordinated with UTM technologies."""

    netrid_dp: Optional[NetRIDDisplayProviderSpecification]
    """User is a NetRID display provider serving virtual observers."""
