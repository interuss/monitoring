import datetime

import s2sphere
from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.astm.f3411.v19.api import Volume4D

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# This scope is used only for experimentation during UPP2
UPP2_SCOPE_ENHANCED_DETAILS = "rid.read.enhanced_details"


def geo_polygon_string(vertices: list[dict[str, float]]) -> str:
    return ",".join("{},{}".format(v["lat"], v["lng"]) for v in vertices)


def geo_polygon_string_from_s2(vertices: list[s2sphere.LatLng]) -> str:
    return ",".join(f"{v.lat().degrees},{v.lng().degrees}" for v in vertices)


def make_volume_4d(
    vertices: list[s2sphere.LatLng],
    alt_lo: float,
    alt_hi: float,
    start_time: datetime.datetime | None,
    end_time: datetime.datetime | None,
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
    def errors(self) -> list[str]:
        errors: list[str] = []
        if "flights_url" not in self:
            errors.append("flights_url field missing")
        return errors

    @property
    def id(self) -> str | None:
        return self.get("id", None)

    @property
    def owner(self) -> str | None:
        return self.get("owner", None)

    @property
    def flights_url(self) -> str | None:
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
    def version(self) -> str | None:
        return self.get("version", None)
