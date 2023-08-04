from typing import List, Optional

from implicitdict import ImplicitDict
from uas_standards.astm.f3411 import v22a


# Mirrors of types defined in remote ID automated testing observation API


class Position(ImplicitDict):
    lat: float
    lng: float
    alt: Optional[float]


class Path(ImplicitDict):
    positions: List[Position]


class Cluster(ImplicitDict):
    corners: List[Position]
    area_sqm: float
    number_of_flights: int


class Flight(ImplicitDict):
    id: str
    most_recent_position: Optional[Position]
    recent_paths: Optional[List[Path]]


class GetDetailsResponse(v22a.api.RIDFlightDetails):
    # TODO: Update automated_testing_interface instead of using the ASTM details response schema
    pass


class GetDisplayDataResponse(ImplicitDict):
    flights: List[Flight] = []
    clusters: List[Cluster] = []
