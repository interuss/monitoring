import argparse
import datetime
import random
import uuid
from collections import namedtuple

import client
import locust
import requests
from geo_utils import create_random_flight_path_volume
from utils import format_time

from monitoring.monitorlib.testing import make_fake_url

Cluster = namedtuple("Cluster", ["lng", "lat", "uuid", "version"])
clusters = []


@locust.events.init_command_line_parser.add_listener
def init_parser(parser: argparse.ArgumentParser):
    """Setup config params, populated by locust.conf."""

    parser.add_argument(
        "--uss-base-url",
        type=str,
        help="Base URL of the USS",
        required=True,
    )
    parser.add_argument(
        "--cluster-count",
        type=int,
        help="Number of clusters to create. One subscription will be created per cluster per client.",
        required=True,
    )
    parser.add_argument(
        "--base-lat",
        type=float,
        help="Latitude of the center of the first cluster",
        required=True,
    )
    parser.add_argument(
        "--base-lng",
        type=float,
        help="Longitude of the center of the first cluster",
        required=True,
    )
    parser.add_argument(
        "--area-radius",
        type=int,
        help="Radius (in meters) of clusters.",
        required=True,
    )
    parser.add_argument(
        "--max-flight-distance",
        type=int,
        help="Maximum distance to cover for an individual flight",
        required=True,
    )
    parser.add_argument(
        "--oi-duration",
        type=int,
        help="Duration (in seconds) of the operational intent",
        default=10,
    )


@locust.events.test_start.add_listener
def create_subscriptions(environment):
    print("Creating subscriptions...")

    lat = environment.parsed_options.base_lat
    lng = environment.parsed_options.base_lng
    radius = environment.parsed_options.area_radius

    time_start = datetime.datetime.now(datetime.UTC)
    time_end = time_start + datetime.timedelta(minutes=60)

    for _ in range(environment.parsed_options.cluster_count):
        sub_uuid = str(uuid.uuid4())
        response = requests.put(
            f"{environment.host}/dss/v1/subscriptions/{sub_uuid}",
            auth=client.get_auth_from_env(),
            json={
                "extents": {
                    "volume": {
                        "outline_circle": {
                            "center": {"lng": lng, "lat": lat},
                            "radius": {"value": radius, "units": "M"},
                        },
                        "altitude_lower": {
                            "value": 0,
                            "reference": "W84",
                            "units": "M",
                        },
                        "altitude_upper": {
                            "value": 10000,
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
                },
                "uss_base_url": make_fake_url(),
                "notify_for_operational_intents": True,
            },
        )

        if response.status_code == 200:
            clusters.append(
                Cluster(
                    lng=lng,
                    lat=lat,
                    uuid=sub_uuid,
                    version=response.json()["subscription"]["version"],
                )
            )
        # Move latitude approximately
        lat += (radius * 2) / 111111
    print(f"Created {len(clusters)} subscriptions.")


@locust.events.test_stop.add_listener
def cleanup_subscriptions(environment):
    print("Cleaning up subscriptions...")

    for cluster in clusters:
        requests.delete(
            f"{environment.host}/dss/v1/subscriptions/{cluster.uuid}/{cluster.version}",
            auth=client.get_auth_from_env(),
        )


class SCD(client.USS):
    wait_time = locust.between(0.01, 0.1)

    def on_start(self):
        self.uss_base_url = self.environment.parsed_options.uss_base_url
        self.radius = self.environment.parsed_options.area_radius
        self.max_flight_distance = self.environment.parsed_options.max_flight_distance
        self.oi_duration = self.environment.parsed_options.oi_duration

        self.clusters = clusters

    @locust.task
    def task_put_intent(self):
        cluster = random.choice(self.clusters)

        entity_id = uuid.uuid4().hex
        with self.lock:
            key = list(self.oi_dict.values())

        body = {
            "state": "Accepted",
            "uss_base_url": self.uss_base_url,
            "new_subscription": {
                "uss_base_url": self.uss_base_url,
            },
            "extents": create_random_flight_path_volume(
                cluster.lat,
                cluster.lng,
                self.radius,
                self.max_flight_distance,
                self.oi_duration,
            ),
            "key": key,
        }
        resp = self.client.put(
            f"/dss/v1/operational_intent_references/{entity_id}",
            json=body,
            name="/dss/v1/operational_intent_references/[id]",
        )
        if resp.status_code in (200, 201):
            ovn = resp.json()["operational_intent_reference"]["ovn"]
            with self.lock:
                self.oi_dict[entity_id] = ovn
