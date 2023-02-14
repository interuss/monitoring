from typing import Dict, List, Optional
import s2sphere

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# This scope is used only for experimentation during UPP2
UPP2_SCOPE_ENHANCED_DETAILS = "rid.read.enhanced_details"


def geo_polygon_string(vertices: List[Dict[str, float]]) -> str:
    return ",".join("{},{}".format(v["lat"], v["lng"]) for v in vertices)


def vertices_from_latlng_rect(rect: s2sphere.LatLngRect) -> List[Dict[str, float]]:
    return [
        {"lat": rect.lat_lo().degrees, "lng": rect.lng_lo().degrees},
        {"lat": rect.lat_lo().degrees, "lng": rect.lng_hi().degrees},
        {"lat": rect.lat_hi().degrees, "lng": rect.lng_hi().degrees},
        {"lat": rect.lat_hi().degrees, "lng": rect.lng_lo().degrees},
    ]


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
