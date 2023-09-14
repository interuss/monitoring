import math
from enum import Enum
from typing import List, Tuple, Union, Optional
import s2sphere
from implicitdict import ImplicitDict, StringBasedDateTime

EARTH_CIRCUMFERENCE_KM = 40075
EARTH_CIRCUMFERENCE_M = EARTH_CIRCUMFERENCE_KM * 1000
EARTH_RADIUS_M = 40075 * 1000 / (2 * math.pi)
EARTH_AREA_M2 = 4 * math.pi * math.pow(EARTH_RADIUS_M, 2)


class DistanceUnits(str, Enum):
    M = "M"
    """Meters"""

    FT = "FT"
    """Feet"""


class LatLngPoint(ImplicitDict):
    lat: float
    lng: float


class Radius(ImplicitDict):
    value: float
    units: DistanceUnits


class Polygon(ImplicitDict):
    vertices: List[LatLngPoint]


class Circle(ImplicitDict):
    center: LatLngPoint
    radius: Radius


class AltitudeDatum(str, Enum):
    W84 = "W84"
    """WGS84 reference ellipsoid"""

    SFC = "SFC"
    """Surface of the ground"""


class Altitude(ImplicitDict):
    value: float
    reference: AltitudeDatum
    units: DistanceUnits


class Volume3D(ImplicitDict):
    outline_circle: Optional[Circle] = None
    outline_polygon: Optional[Polygon] = None
    altitude_lower: Optional[Altitude] = None
    altitude_upper: Optional[Altitude] = None

    def altitude_lower_wgs84_m(self, default_value: Optional[float] = None) -> float:
        if self.altitude_lower is None:
            if default_value is None:
                raise ValueError("Lower altitude was not specified")
            else:
                return default_value
        if self.altitude_lower.reference != AltitudeDatum.W84:
            raise NotImplementedError(
                f"Cannot compute lower altitude WGS84 meters with reference {self.altitude_lower.reference}"
            )
        if self.altitude_lower.units != DistanceUnits.M:
            raise NotImplementedError(
                f"Cannot compute lower altitude WGS84 meters with units {self.altitude_lower.units}"
            )
        return self.altitude_lower.value

    def altitude_upper_wgs84_m(self, default_value: Optional[float] = None) -> float:
        if self.altitude_upper is None:
            if default_value is None:
                raise ValueError("Upper altitude was not specified")
            else:
                return default_value
        if self.altitude_upper.reference != AltitudeDatum.W84:
            raise NotImplementedError(
                f"Cannot compute upper altitude WGS84 meters with reference {self.altitude_upper.reference}"
            )
        if self.altitude_upper.units != DistanceUnits.M:
            raise NotImplementedError(
                f"Cannot compute upper altitude WGS84 meters with units {self.altitude_upper.units}"
            )
        return self.altitude_upper.value


class Volume4D(ImplicitDict):
    """Generic representation of a 4D volume, usable across multiple standards and formats."""

    volume: Volume3D
    time_start: Optional[StringBasedDateTime] = None
    time_end: Optional[StringBasedDateTime] = None


def make_latlng_rect(area) -> s2sphere.LatLngRect:
    """Make an S2 LatLngRect from the provided input.

    Args:
        area: May be one of multiple types:
          str: Interpreted as rect "spec" with the form lat,lng,lat,lng
          Volume3D: Generic 3D volume

    Returns:
        LatLngRect enclosing provided area.
    """
    if isinstance(area, str):
        coords = area.split(",")
        if len(coords) != 4:
            raise ValueError(
                "Expected lat,lng,lat,lng; found %d coordinates instead" % len(coords)
            )
        lat1 = validate_lat(coords[0])
        lng1 = validate_lng(coords[1])
        lat2 = validate_lat(coords[2])
        lng2 = validate_lng(coords[3])
        p1 = s2sphere.LatLng.from_degrees(lat1, lng1)
        p2 = s2sphere.LatLng.from_degrees(lat2, lng2)
        return s2sphere.LatLngRect.from_point_pair(p1, p2)
    elif isinstance(area, Volume3D):
        if "outline_polygon" in area and area.outline_polygon:
            lat_min = min(v.lat for v in area.outline_polygon.vertices)
            lat_max = max(v.lat for v in area.outline_polygon.vertices)
            lng_min = min(v.lng for v in area.outline_polygon.vertices)
            lng_max = max(v.lng for v in area.outline_polygon.vertices)
        elif "outline_circle" in area and area.outline_circle:
            p0 = s2sphere.LatLng.from_degrees(
                area.outline_circle.center.lng, area.outline_circle.center.lat
            )
            lat_min = (
                unflatten(p0, (0, -area.outline_circle.radius.value)).lat().degrees
            )
            lat_max = unflatten(p0, (0, area.outline_circle.radius.value)).lat().degrees
            lng_min = (
                unflatten(p0, (-area.outline_circle.radius.value, 0)).lng().degrees
            )
            lng_max = unflatten(p0, (area.outline_circle.radius.value, 0)).lng().degrees
        else:
            raise ValueError("Volume3D outline was not properly defined")
        p1 = s2sphere.LatLng.from_degrees(lat_min, lng_min)
        p2 = s2sphere.LatLng.from_degrees(lat_max, lng_max)
        return s2sphere.LatLngRect.from_point_pair(p1, p2)
    else:
        raise NotImplementedError(
            f"make_latlng_rect does not support {type(area).__name__}"
        )


def validate_lat(lat: str) -> float:
    lat = float(lat)
    if lat < -90 or lat > 90:
        raise ValueError("Latitude must be in [-90, 90] range")
    return lat


def validate_lng(lng: str) -> float:
    lng = float(lng)
    if lng < -180 or lng > 180:
        raise ValueError("Longitude must be in [-180, 180] range")
    return lng


def flatten(reference: s2sphere.LatLng, point: s2sphere.LatLng) -> Tuple[float, float]:
    """Locally flatten a lat-lng point to (dx, dy) in meters from reference."""
    return (
        (point.lng().degrees - reference.lng().degrees)
        * EARTH_CIRCUMFERENCE_KM
        * math.cos(reference.lat().radians)
        * 1000
        / 360,
        (point.lat().degrees - reference.lat().degrees)
        * EARTH_CIRCUMFERENCE_KM
        * 1000
        / 360,
    )


def unflatten(
    reference: s2sphere.LatLng, point: Tuple[float, float]
) -> s2sphere.LatLng:
    """Locally unflatten a (dx, dy) point to an absolute lat-lng point."""
    return s2sphere.LatLng.from_degrees(
        reference.lat().degrees + point[1] * 360 / (EARTH_CIRCUMFERENCE_KM * 1000),
        reference.lng().degrees
        + point[0]
        * 360
        / (EARTH_CIRCUMFERENCE_KM * 1000 * math.cos(reference.lat().radians)),
    )


def area_of_latlngrect(rect: s2sphere.LatLngRect) -> float:
    """Compute the approximate surface area within a lat-lng rectangle."""
    return EARTH_AREA_M2 * rect.area() / (4 * math.pi)


def bounding_rect(latlngs: List[Tuple[float, float]]) -> s2sphere.LatLngRect:
    lat_min = 90
    lat_max = -90
    lng_min = 360
    lng_max = -360
    for (lat, lng) in latlngs:
        lat_min = min(lat_min, lat)
        lat_max = max(lat_max, lat)
        lng_min = min(lng_min, lng)
        lng_max = max(lng_max, lng)
    return s2sphere.LatLngRect.from_point_pair(
        s2sphere.LatLng.from_degrees(lat_min, lng_min),
        s2sphere.LatLng.from_degrees(lat_max, lng_max),
    )


def get_latlngrect_diagonal_km(rect: s2sphere.LatLngRect) -> float:
    """Compute the distance in km between two opposite corners of the rect"""
    return rect.lo().get_distance(rect.hi()).degrees * EARTH_CIRCUMFERENCE_KM / 360


def get_latlngrect_vertices(rect: s2sphere.LatLngRect) -> List[s2sphere.LatLng]:
    """Returns the rect as a list of vertices"""
    return [
        s2sphere.LatLng.from_angles(lat=rect.lat_lo(), lng=rect.lng_lo()),
        s2sphere.LatLng.from_angles(lat=rect.lat_lo(), lng=rect.lng_hi()),
        s2sphere.LatLng.from_angles(lat=rect.lat_hi(), lng=rect.lng_hi()),
        s2sphere.LatLng.from_angles(lat=rect.lat_hi(), lng=rect.lng_lo()),
    ]


class LatLngBoundingBox(ImplicitDict):
    """Bounding box in latitude and longitude"""

    lat_min: float
    """Lower latitude bound (degrees)"""

    lng_min: float
    """Lower longitude bound (degrees)"""

    lat_max: float
    """Upper latitude bound (degrees)"""

    lng_max: float
    """Upper longitude bound (degrees)"""

    def to_vertices(self) -> List[s2sphere.LatLng]:
        return [
            s2sphere.LatLng.from_degrees(self.lat_min, self.lng_min),
            s2sphere.LatLng.from_degrees(self.lat_max, self.lng_min),
            s2sphere.LatLng.from_degrees(self.lat_max, self.lng_max),
            s2sphere.LatLng.from_degrees(self.lat_min, self.lng_max),
        ]


class LatLngVertex(ImplicitDict):
    """Vertex in latitude and longitude"""

    lat: float
    """Latitude (degrees)"""

    lng: float
    """Longitude (degrees)"""

    def as_s2sphere(self) -> s2sphere.LatLng:
        return s2sphere.LatLng.from_degrees(self.lat, self.lng)
