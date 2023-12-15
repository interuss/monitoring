from __future__ import annotations
import math
from enum import Enum
import os
from typing import List, Tuple, Union, Optional

from implicitdict import ImplicitDict
import numpy as np
import s2sphere
from s2sphere import LatLng
from scipy.interpolate import RectBivariateSpline as Spline
import shapely.geometry

from monitoring.monitorlib.transformations import (
    Transformation,
    RelativeTranslation,
    AbsoluteTranslation,
)
from uas_standards.astm.f3548.v21 import api as f3548v21
from uas_standards.astm.f3411.v19 import api as f3411v19
from uas_standards.astm.f3411.v22a import api as f3411v22a
from uas_standards.interuss.automated_testing.rid.v1 import (
    injection as f3411testing_injection,
)
from uas_standards.interuss.automated_testing.flight_planning.v1 import api as fp_api

EARTH_CIRCUMFERENCE_KM = 40075
EARTH_CIRCUMFERENCE_M = EARTH_CIRCUMFERENCE_KM * 1000
EARTH_RADIUS_M = 40075 * 1000 / (2 * math.pi)
EARTH_AREA_M2 = 4 * math.pi * math.pow(EARTH_RADIUS_M, 2)
METERS_PER_FOOT = 0.3048

DISTANCE_TOLERANCE_M = 0.01
COORD_TOLERANCE_DEG = 360 / EARTH_CIRCUMFERENCE_M * DISTANCE_TOLERANCE_M


class DistanceUnits(str, Enum):
    M = "M"
    """Meters"""

    FT = "FT"
    """Feet"""

    def in_meters(self, value: float) -> float:
        if self == DistanceUnits.M:
            return value
        elif self == DistanceUnits.FT:
            return value * METERS_PER_FOOT
        else:
            raise NotImplementedError(f"Cannot convert from '{self}' to meters")


class LatLngPoint(ImplicitDict):
    """Vertex in latitude and longitude"""

    lat: float
    """Latitude (degrees)"""

    lng: float
    """Longitude (degrees)"""

    @staticmethod
    def from_f3411(
        position: Union[
            f3411v19.RIDAircraftPosition,
            f3411v22a.RIDAircraftPosition,
            f3411testing_injection.RIDAircraftPosition,
        ]
    ):
        return LatLngPoint(
            lat=position.lat,
            lng=position.lng,
        )

    def to_flight_planning_api(self) -> fp_api.LatLngPoint:
        return fp_api.LatLngPoint(lat=self.lat, lng=self.lng)

    @staticmethod
    def from_s2(p: s2sphere.LatLng) -> LatLngPoint:
        return LatLngPoint(lat=p.lat().degrees, lng=p.lng().degrees)

    def as_s2sphere(self) -> s2sphere.LatLng:
        return s2sphere.LatLng.from_degrees(self.lat, self.lng)

    def match(self, other: LatLngPoint) -> bool:
        """Determine whether two points may be mistaken for each other."""
        return (
            abs(self.lat - other.lat) < COORD_TOLERANCE_DEG
            and abs(self.lng - other.lng) < COORD_TOLERANCE_DEG
        )


class Radius(ImplicitDict):
    value: float
    units: DistanceUnits

    def in_meters(self) -> float:
        return self.units.in_meters(self.value)


class Polygon(ImplicitDict):
    vertices: Optional[List[LatLngPoint]]

    def vertex_average(self) -> LatLngPoint:
        lat = sum(p.lat for p in self.vertices) / len(self.vertices)
        lng = sum(p.lng for p in self.vertices) / len(self.vertices)
        return LatLngPoint(lat=lat, lng=lng)

    @staticmethod
    def from_coords(coords: List[Tuple[float, float]]) -> Polygon:
        return Polygon(
            vertices=[LatLngPoint(lat=lat, lng=lng) for (lat, lng) in coords]
        )

    @staticmethod
    def from_latlng_rect(latlngrect: s2sphere.LatLngRect) -> Polygon:
        return Polygon(
            vertices=[
                LatLngPoint(
                    lat=latlngrect.lat_lo().degrees, lng=latlngrect.lng_lo().degrees
                ),
                LatLngPoint(
                    lat=latlngrect.lat_lo().degrees, lng=latlngrect.lng_hi().degrees
                ),
                LatLngPoint(
                    lat=latlngrect.lat_hi().degrees, lng=latlngrect.lng_hi().degrees
                ),
                LatLngPoint(
                    lat=latlngrect.lat_hi().degrees, lng=latlngrect.lng_lo().degrees
                ),
            ]
        )

    @staticmethod
    def from_f3548v21(vol: Union[f3548v21.Polygon, dict]) -> Polygon:
        if not isinstance(vol, f3548v21.Polygon) and isinstance(vol, dict):
            vol = ImplicitDict.parse(vol, f3548v21.Polygon)
        return Polygon(
            vertices=[ImplicitDict.parse(p, LatLngPoint) for p in vol.vertices]
        )


class Circle(ImplicitDict):
    center: LatLngPoint
    radius: Radius

    @staticmethod
    def from_meters(
        lat_degrees: float, lng_degrees: float, radius_meters: float
    ) -> Circle:
        return Circle(
            center=LatLngPoint(lat=lat_degrees, lng=lng_degrees),
            radius=Radius(value=radius_meters, units="M"),
        )

    @staticmethod
    def from_f3548v21(vol: Union[f3548v21.Circle, dict]) -> Circle:
        if not isinstance(vol, f3548v21.Circle) and isinstance(vol, dict):
            vol = ImplicitDict.parse(vol, f3548v21.Circle)
        return Circle(
            center=ImplicitDict.parse(vol.center, LatLngPoint),
            radius=ImplicitDict.parse(vol.radius, Radius),
        )


class AltitudeDatum(str, Enum):
    W84 = "W84"
    """WGS84 reference ellipsoid"""

    SFC = "SFC"
    """Surface of the ground"""


class Altitude(ImplicitDict):
    value: float
    reference: AltitudeDatum
    units: DistanceUnits

    @staticmethod
    def w84m(value: Optional[float]) -> Optional[Altitude]:
        if value is None:
            return None
        return Altitude(value=value, reference=AltitudeDatum.W84, units=DistanceUnits.M)

    def to_flight_planning_api(self) -> fp_api.Altitude:
        return fp_api.Altitude(
            value=self.units.in_meters(self.value),
            reference=fp_api.AltitudeReference(self.reference),
            units=fp_api.AltitudeUnits.M,
        )

    @staticmethod
    def from_f3548v21(vol: Union[f3548v21.Altitude, dict]) -> Altitude:
        return ImplicitDict.parse(vol, Altitude)


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

    def intersects_vol3(self, vol3_2: Volume3D) -> bool:
        vol3_1 = self
        if vol3_1.altitude_upper.value < vol3_2.altitude_lower.value:
            return False
        if vol3_1.altitude_lower.value > vol3_2.altitude_upper.value:
            return False

        if vol3_1.outline_circle:
            circle = vol3_1.outline_circle
            if circle.radius.units != "M":
                raise NotImplementedError(
                    "Unsupported circle radius units: {}".format(circle.radius.units)
                )
            ref = s2sphere.LatLng.from_degrees(circle.center.lat, circle.center.lng)
            footprint1 = shapely.geometry.Point(0, 0).buffer(
                vol3_1.outline_circle.radius.value
            )
        elif vol3_1.outline_polygon:
            p = vol3_1.outline_polygon.vertices[0]
            ref = s2sphere.LatLng.from_degrees(p.lat, p.lng)
            footprint1 = shapely.geometry.Polygon(
                flatten(ref, s2sphere.LatLng.from_degrees(v.lat, v.lng))
                for v in vol3_1.outline_polygon.vertices
            )
        else:
            raise ValueError("Neither outline_circle nor outline_polygon specified")

        if vol3_2.outline_circle:
            circle = vol3_2.outline_circle
            if circle.radius.units != "M":
                raise NotImplementedError(
                    "Unsupported circle radius units: {}".format(circle.radius.units)
                )
            xy = flatten(
                ref, s2sphere.LatLng.from_degrees(circle.center.lat, circle.center.lng)
            )
            footprint2 = shapely.geometry.Point(*xy).buffer(circle.radius.value)
        elif vol3_2.outline_polygon:
            footprint2 = shapely.geometry.Polygon(
                flatten(ref, s2sphere.LatLng.from_degrees(v.lat, v.lng))
                for v in vol3_2.outline_polygon.vertices
            )
        else:
            raise ValueError("Neither outline_circle nor outline_polygon specified")

        return footprint1.intersects(footprint2)

    def transform(self, transformation: Transformation):
        if (
            "relative_translation" in transformation
            and transformation.relative_translation
        ):
            return self.translate_relative(transformation.relative_translation)
        elif (
            "absolute_translation" in transformation
            and transformation.absolute_translation
        ):
            return self.translate_absolute(transformation.absolute_translation)
        raise ValueError(
            f"No supported transformation defined (keys: {', '.join(transformation)})"
        )

    def translate_relative(self, translation: RelativeTranslation) -> Volume3D:
        def offset(p0: LatLngPoint, p: LatLngPoint) -> LatLngPoint:
            s2_p0 = p0.as_s2sphere()
            xy = flatten(s2_p0, p.as_s2sphere())
            if "meters_east" in translation and translation.meters_east:
                xy = (xy[0] + translation.meters_east, xy[1])
            if "meters_north" in translation and translation.meters_north:
                xy = (xy[0], xy[1] + translation.meters_north)
            p1 = LatLngPoint.from_s2(unflatten(s2_p0, xy))
            if "degrees_east" in translation and translation.degrees_east:
                p1.lng += translation.degrees_east
            if "degrees_north" in translation and translation.degrees_north:
                p1.lat += translation.degrees_north
            return p1

        kwargs = {k: v for k, v in self.items() if v is not None}
        if self.outline_circle is not None:
            kwargs["outline_circle"] = Circle(
                center=offset(self.outline_circle.center, self.outline_circle.center),
                radius=self.outline_circle.radius,
            )
        if self.outline_polygon is not None:
            ref0 = self.outline_polygon.vertex_average()
            vertices = [offset(ref0, p) for p in self.outline_polygon.vertices]
            kwargs["outline_polygon"] = Polygon(vertices=vertices)
        result = Volume3D(**kwargs)
        if "meters_up" in translation and translation.meters_up:
            if result.altitude_lower:
                if result.altitude_lower.units == DistanceUnits.M:
                    result.altitude_lower.value += translation.meters_up
                else:
                    raise NotImplementedError(
                        f"Cannot yet translate meters_up with {result.altitude_lower.units} lower altitude units"
                    )
            if result.altitude_upper:
                if result.altitude_upper.units == DistanceUnits.M:
                    result.altitude_upper.value += translation.meters_up
                else:
                    raise NotImplementedError(
                        f"Cannot yet translate meters_up with {result.altitude_lower.units} upper altitude units"
                    )
        return result

    def translate_absolute(self, translation: AbsoluteTranslation) -> Volume3D:
        new_center = LatLngPoint(
            lat=translation.new_latitude, lng=translation.new_longitude
        )
        kwargs = {k: v for k, v in self.items() if v is not None}
        if self.outline_circle is not None:
            kwargs["outline_circle"] = Circle(
                center=new_center, radius=self.outline_circle.radius
            )
        if self.outline_polygon is not None:
            ref0 = self.outline_polygon.vertex_average().as_s2sphere()
            xy = [flatten(ref0, p.as_s2sphere()) for p in self.outline_polygon.vertices]
            ref1 = new_center.as_s2sphere()
            vertices = [LatLngPoint.from_s2(unflatten(ref1, p)) for p in xy]
            kwargs["outline_polygon"] = Polygon(vertices=vertices)
        return Volume3D(**kwargs)

    @staticmethod
    def from_flight_planning_api(vol: fp_api.Volume3D) -> Volume3D:
        return ImplicitDict.parse(vol, Volume3D)

    def to_flight_planning_api(self) -> fp_api.Volume3D:
        kwargs = {}
        if self.outline_circle:
            kwargs["outline_circle"] = fp_api.Circle(
                center=self.outline_circle.center.to_flight_planning_api(),
                radius=fp_api.Radius(
                    value=self.outline_circle.radius.in_meters(),
                    units=fp_api.RadiusUnits.M,
                ),
            )
        if self.outline_polygon:
            kwargs["outline_polygon"] = fp_api.Polygon(
                vertices=[
                    v.to_flight_planning_api() for v in self.outline_polygon.vertices
                ]
            )
        if self.altitude_lower:
            kwargs["altitude_lower"] = self.altitude_lower.to_flight_planning_api()
        if self.altitude_upper:
            kwargs["altitude_upper"] = self.altitude_upper.to_flight_planning_api()
        return fp_api.Volume3D(**kwargs)

    @staticmethod
    def from_f3548v21(vol: Union[f3548v21.Volume3D, dict]) -> Volume3D:
        if not isinstance(vol, f3548v21.Volume3D) and isinstance(vol, dict):
            vol = ImplicitDict.parse(vol, f3548v21.Volume3D)
        kwargs = {}
        if "outline_circle" in vol and vol.outline_circle:
            kwargs["outline_circle"] = Circle.from_f3548v21(vol.outline_circle)
        if "outline_polygon" in vol and vol.outline_polygon:
            kwargs["outline_polygon"] = Polygon.from_f3548v21(vol.outline_polygon)
        if "altitude_lower" in vol and vol.altitude_lower:
            kwargs["altitude_lower"] = Altitude.from_f3548v21(vol.altitude_lower)
        if "altitude_upper" in vol and vol.altitude_upper:
            kwargs["altitude_upper"] = Altitude.from_f3548v21(vol.altitude_upper)
        return Volume3D(**kwargs)

    def to_f3548v21(self) -> f3548v21.Volume3D:
        return ImplicitDict.parse(self, f3548v21.Volume3D)


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


def validate_lat(lat: Union[str, float]) -> float:
    lat = float(lat)
    if lat < -90 or lat > 90:
        raise ValueError("Latitude must be in [-90, 90] range")
    return lat


def validate_lng(lng: Union[str, float]) -> float:
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


def latitude_degrees(distance_meters: float) -> float:
    return 360 * distance_meters / EARTH_CIRCUMFERENCE_M


_egm96: Optional[Spline] = None
"""Cached EGM96 geoid interpolation function with inverted latitude"""


def egm96_geoid_offset(p: s2sphere.LatLng) -> float:
    """Estimate the EGM96 geoid height above the WGS84 ellipsoid.

    Args:
        p: Point where offset should be estimated.

    Returns: Meters above WGS84 ellipsoid of the EGM96 geoid at p.
    """
    global _egm96
    if _egm96 is None:
        grid_size = 0.25  # degrees
        # Latitude data is [90, -90] degrees
        lats = np.arange(-90, 90 + grid_size / 2, grid_size)
        # Longitude data is [0, 360) degrees
        lngs = np.arange(0, 360, grid_size)
        grid_path = os.path.join(os.path.dirname(__file__), "assets/WW15MGH.DAC")
        grid = np.fromfile(grid_path, ">i2").reshape(lats.size, lngs.size) / 100
        _egm96 = Spline(lats, lngs, grid)
    lng = math.fmod(p.lng().degrees, 360)
    while lng < 0:
        lng += 360
    lat = p.lat().degrees
    if lat < -90 or lat > 90:
        raise ValueError(f"Cannot compute EGM96 geoid offset at latitude {lat} degrees")

    # Negative latitude because the grid file lists offsets from 90 to -90
    # degrees latitude, but Splines must have increasing X so latitudes must be
    # listed -90 to 90.  Since latitude data are symmetric, we can simply
    # convert "-90 to 90" to "90 to -90" by inverting the requested latitude.
    return _egm96.ev(-lat, lng)


def generate_slight_overlap_area(in_points: List[LatLng]) -> List[LatLng]:
    """
    Takes a list of LatLng points and returns a list of LatLng points that represents
    a polygon only slightly overlapping with the input, and that is roughly half the diameter of the input.

    The returned polygon is built from the first point of the input, from which a square
    is drawn in the direction opposite of the center of the input polygon.

    """
    overlap_corner = in_points[0]  # the spot that will have a tiny overlap

    # Compute the center of mass of the input polygon
    center = LatLng.from_degrees(
        sum([point.lat().degrees for point in in_points]) / len(in_points),
        sum([point.lng().degrees for point in in_points]) / len(in_points),
    )

    delta_lat = center.lat().degrees - overlap_corner.lat().degrees
    delta_lng = center.lng().degrees - overlap_corner.lng().degrees

    same_lat_point = LatLng.from_degrees(
        overlap_corner.lat().degrees, overlap_corner.lng().degrees - delta_lng
    )
    same_lng_point = LatLng.from_degrees(
        overlap_corner.lat().degrees - delta_lat, overlap_corner.lng().degrees
    )

    opposite_corner = LatLng.from_degrees(
        overlap_corner.lat().degrees - delta_lat,
        overlap_corner.lng().degrees - delta_lng,
    )

    return [overlap_corner, same_lat_point, opposite_corner, same_lng_point]
