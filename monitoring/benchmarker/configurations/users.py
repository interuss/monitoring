from typing import Optional

from implicitdict import ImplicitDict, StringBasedDateTime, StringBasedTimeDelta

from monitoring.benchmarker.configurations.user.astm import scd
from monitoring.benchmarker.configurations.user.astm.dss import ASTMDSSSelectionStrategy
from monitoring.monitorlib.geo import Altitude, LatLngPoint
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.definitions import ResourceID


class BenchmarkUserName(str):
    """Unique (within benchmark configuration) name for a means to generate load."""


class FixedLocationSpecification(ImplicitDict):
    horizontal: LatLngPoint
    vertical: Altitude


class FlightTimeGenerationSpecification(ImplicitDict):
    fixed_spacing: Optional[StringBasedTimeDelta]
    """Add this fixed delay between the end of the previous flight and the start of the next flight."""

    uniform_random_spacing: Optional[StringBasedTimeDelta]
    """Add a random delay uniformly distributed between 0 and this duration between the end of the previous flight and the start of the next flight."""


class FlightLocationGenerationSpecification(ImplicitDict):
    fixed_location: Optional[FixedLocationSpecification]
    """Always choose the same flight location."""


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


class BenchmarkUserSpecification(ImplicitDict):
    name: BenchmarkUserName

    flight_planner: Optional[FlightPlannerSpecification]
    """User is a USS client that plans flights coordinated with UTM technologies."""
