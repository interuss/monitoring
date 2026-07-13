from enum import StrEnum
from typing import Optional

from implicitdict import ImplicitDict, StringBasedDateTime, StringBasedTimeDelta

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
    """Set delay between the end of the previous flight and the start of the next flight to this value."""


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
    """Means to generate flight shapes."""


class FlightGenerationSpecification(ImplicitDict):
    independent_time_location_shape: Optional[
        IndependentComponentsFlightGenerationSpecification
    ]
    """The time, location, and shape of flights are generated independently."""


class ASTMNetRIDISAPerFlightStrategySpecification(ImplicitDict):
    """Create an ISA per flight."""

    before_flight_start: StringBasedTimeDelta
    """Create the ISA this amount of time before the start of the flight."""

    after_flight_end: Optional[StringBasedTimeDelta]
    """Delete the ISA this amount of time after the end of this flight."""


class ASTMNetRIDISAStrategySpecification(ImplicitDict):
    """Strategy used to ensure at least one ISA covers every flight."""

    isa_per_flight: Optional[ASTMNetRIDISAPerFlightStrategySpecification]


class ASTMDSSSelectionStrategy(StrEnum):
    First = "First"
    """Always use the first DSS in the pool list."""

    Random = "Random"
    """Use a random DSS from the pool list for every operation."""


class ASTMNetRIDBehaviorSpecification(ImplicitDict):
    rid_version: RIDVersion

    dss_pool: list[ResourceID]
    """Means to interact with the ASTM DSS.
    
    Benchmark configuration must contain a `resources.astm.f3411.DSSInstanceResource` resource with each of these names."""

    dss_selection_strategy: Optional[ASTMDSSSelectionStrategy]

    isa_strategy: Optional[ASTMNetRIDISAStrategySpecification]


class FlightPlannerSpecification(ImplicitDict):
    """User planning flights coordinated via UTM standards."""

    flight_generation: FlightGenerationSpecification
    """How flight planner generates their flights."""

    astm_netrid_behavior: Optional[ASTMNetRIDBehaviorSpecification]
    """How flight planner provides ASTM NetRID service for their flights."""


class BenchmarkUserSpecification(ImplicitDict):
    name: BenchmarkUserName

    flight_planner: Optional[FlightPlannerSpecification]
    """User is a USS client that plans flights coordinated with UTM technologies."""
