"""Loaded by default by the Locust testing framework."""

import argparse
import datetime
import random
import uuid

import client
import geo_utils
import locust
import shapely


@locust.events.init_command_line_parser.add_listener
def init_parser(parser: argparse.ArgumentParser):
    """Setup config params, populated by locust.conf."""

    parser.add_argument(
        "--uss-base-url",
        type=str,
        help="Base URL of the Token Exchanger from which to request JWTs",
        required=True,
    )
    parser.add_argument(
        "--area-lat",
        type=float,
        help="Latitude of the center of the area in which to create flights",
        required=True,
    )
    parser.add_argument(
        "--area-lng",
        type=float,
        help="Longitude of the center of the area in which to create flights",
        required=True,
    )
    parser.add_argument(
        "--area-radius",
        type=int,
        help="Radius (in meters) of the area in which to create flights",
        required=True,
    )
    parser.add_argument(
        "--max-flight-distance",
        type=int,
        help="Maximum distance to cover for an individual flight",
        required=True,
    )


def _format_time(time: datetime.datetime) -> str:
    return time.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _create_volume(
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
            "value": _format_time(time_start),
            "format": "RFC3339",
        },
        "time_end": {
            "value": _format_time(time_end),
            "format": "RFC3339",
        },
    }


def _create_random_flight_path(
    lat: float, lng: float, radius: int, max_flight_distance_meters: int
):
    altitude_lower = random.randint(0, 10000)
    altitude_upper = altitude_lower + 1

    start_time = datetime.datetime.now()
    end_time = start_time + datetime.timedelta(seconds=10)

    rects = geo_utils.create_random_flight_path(
        lat, lng, radius, max_flight_distance_meters
    )
    return [
        _create_volume(r, altitude_lower, altitude_upper, start_time, end_time)
        for r in rects.geoms
    ]


class SCD(client.USS):
    wait_time = locust.between(0.01, 0.1)

    def on_start(self):
        self.uss_base_url = self.environment.parsed_options.uss_base_url
        self.lat = self.environment.parsed_options.area_lat
        self.lng = self.environment.parsed_options.area_lng
        self.radius = self.environment.parsed_options.area_radius
        self.max_flight_distance = self.environment.parsed_options.max_flight_distance

    @locust.task
    def task_put_intent(self):
        entity_id = uuid.uuid4().hex

        body = {
            "state": "Accepted",
            "uss_base_url": self.uss_base_url,
            "new_subscription": {
                "uss_base_url": self.uss_base_url,
            },
            "extents": _create_random_flight_path(
                self.lat, self.lng, self.radius, self.max_flight_distance
            ),
        }
        self.client.put(
            f"/dss/v1/operational_intent_references/{entity_id}",
            json=body,
            name="/dss/v1/operational_intent_references/[id]",
        )
