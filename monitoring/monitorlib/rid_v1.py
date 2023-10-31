from typing import Dict, List, Optional
import s2sphere
import datetime

from uas_standards.astm.f3411.v19.api import Volume4D
from implicitdict import ImplicitDict, StringBasedDateTime

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# This scope is used only for experimentation during UPP2
UPP2_SCOPE_ENHANCED_DETAILS = "rid.read.enhanced_details"


def geo_polygon_string(vertices: List[Dict[str, float]]) -> str:
    return ",".join("{},{}".format(v["lat"], v["lng"]) for v in vertices)


def geo_polygon_string_from_s2(vertices: List[s2sphere.LatLng]) -> str:
    return ",".join("{},{}".format(v.lat().degrees, v.lng().degrees) for v in vertices)


def make_volume_4d(
    vertices: List[s2sphere.LatLng],
    alt_lo: float,
    alt_hi: float,
    start_time: Optional[datetime.datetime],
    end_time: Optional[datetime.datetime],
) -> Volume4D:
    return ImplicitDict.parse(
        {
            "spatial_volume": {
                "footprint": {
                    "vertices": [
                        {"lat": vertex.lat().degrees, "lng": vertex.lng().degrees}
                        for vertex in vertices
                    ]
                },
                "altitude_lo": alt_lo,
                "altitude_hi": alt_hi,
            },
            **(
                {"time_start": StringBasedDateTime(start_time)}
                if start_time is not None
                else {}
            ),
            **(
                {"time_end": StringBasedDateTime(end_time)}
                if end_time is not None
                else {}
            ),
        },
        Volume4D,
    )


class ISA(dict):
    @property
    def errors(self) -> List[str]:
        errors: List[str] = []
        if "flights_url" not in self:
            errors.append("flights_url field missing")
        return errors

    @property
    def id(self) -> Optional[str]:
        return self.get("id", None)

    @property
    def owner(self) -> Optional[str]:
        return self.get("owner", None)

    @property
    def flights_url(self) -> Optional[str]:
        return self.get("flights_url", None)


class Flight(dict):
    @property
    def valid(self) -> bool:
        if self.id is None:
            return False
        return True

    @property
    def id(self) -> str:
        return self.get("id", None)


class Subscription(dict):
    @property
    def valid(self) -> bool:
        if self.version is None:
            return False
        return True

    @property
    def version(self) -> Optional[str]:
        return self.get("version", None)
