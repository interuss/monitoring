import datetime
import math
import random

import shapely
from utils import format_time


def _create_rectangle(
    center: shapely.Point,
    width: float,
    height: float,
    rotation_angle_deg: float,
) -> shapely.Polygon:
    rect = shapely.geometry.box(
        center.x - width / 2,
        center.y - height / 2,
        center.x + width / 2,
        center.y + height / 2,
    )
    rotated_rect = shapely.affinity.rotate(rect, rotation_angle_deg)
    return rotated_rect


def _create_rectangles_on_path(
    start_point: shapely.geometry.Point,
    bearing_deg: float,
    distance: float,
    rect_width: float,
    rect_height: float,
) -> shapely.MultiPolygon:
    bearing_rad = math.radians(bearing_deg)

    # Calculate the cartesian step between each rectangle.
    dx = rect_width * math.cos(bearing_rad)
    dy = rect_width * math.sin(bearing_rad)

    # Add one so that we always have at least one rect.
    num_rects = 1 + math.floor(distance / rect_width)
    rectangles = []

    for _ in range(num_rects):
        rectangles.append(
            _create_rectangle(
                start_point,
                rect_width,
                rect_height,
                bearing_deg,
            )
        )
        start_point = shapely.affinity.translate(start_point, dx, dy)

    return shapely.geometry.MultiPolygon(rectangles)


def _random_point_within_circle(
    center: shapely.Point,
    radius: float,
) -> shapely.Point:
    # Take sqrt of random to ensure uniform distribution of points throughout
    # circular area:
    random_radius = radius * math.sqrt(random.random())
    random_angle = 2 * math.pi * random.random()

    x = random_radius * math.cos(random_angle) + center.x
    y = random_radius * math.sin(random_angle) + center.y

    return shapely.geometry.Point(x, y)


def _meters_to_angle(distance: float) -> float:
    # Rough lat/lng angle of one meter at the equator - longitude gets distorted
    # towards the poles.
    return distance / 111320


def create_random_flight_path(
    lat: float, lng: float, radius: int, max_flight_distance_meters: float
) -> shapely.geometry.MultiPolygon:
    bearing_deg = random.random() * 360
    distance_meters = random.random() * max_flight_distance_meters

    # Roughly scale all distance measurements to deg lat/lng:
    radius_angle = _meters_to_angle(radius)
    distance_angle = _meters_to_angle(distance_meters)
    rect_width = _meters_to_angle(100)
    rect_height = _meters_to_angle(10)

    # Create a random start point within the circle of given radius and center:
    center = shapely.geometry.Point(lng, lat)
    start_point = _random_point_within_circle(center, radius_angle)

    return _create_rectangles_on_path(
        start_point,
        bearing_deg,
        distance_angle,
        rect_width,
        rect_height,
    )


def create_random_flight_path_volume(
    lat: float, lng: float, radius: int, max_flight_distance_meters: int
):
    altitude_lower = random.randint(0, 10000)
    altitude_upper = altitude_lower + 1

    start_time = datetime.datetime.now()
    end_time = start_time + datetime.timedelta(seconds=10)

    rects = create_random_flight_path(lat, lng, radius, max_flight_distance_meters)
    return [
        create_volume(r, altitude_lower, altitude_upper, start_time, end_time)
        for r in rects.geoms
    ]


def create_volume(
    polygon: shapely.Polygon,
    altitude_lower: float,
    altitude_upper: float,
    time_start: datetime.datetime,
    time_end: datetime.datetime,
):
    return {
        "volume": {
            "outline_polygon": {
                "vertices": [
                    {"lat": v[1], "lng": v[0]} for v in polygon.exterior.coords[:-1]
                ]
            },
            "altitude_lower": {
                "value": altitude_lower,
                "reference": "W84",
                "units": "M",
            },
            "altitude_upper": {
                "value": altitude_upper,
                "reference": "W84",
                "units": "M",
            },
        },
        "time_start": {
            "value": format_time(time_start),
            "format": "RFC3339",
        },
        "time_end": {
            "value": format_time(time_end),
            "format": "RFC3339",
        },
    }
