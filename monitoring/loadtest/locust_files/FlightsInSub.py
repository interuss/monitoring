import argparse
import datetime
import random
import uuid
from collections import namedtuple

import client
import locust
from geo_utils import create_random_flight_path_volume
from utils import format_time

from monitoring.monitorlib.testing import make_fake_url

Cluster = namedtuple("Cluster", ["lng", "lat", "uuid", "version"])


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


class SCD(client.USS):
    wait_time = locust.between(0.01, 0.1)

    def on_start(self):
        self.uss_base_url = self.environment.parsed_options.uss_base_url
        self.radius = self.environment.parsed_options.area_radius
        self.max_flight_distance = self.environment.parsed_options.max_flight_distance
        self.oi_duration = self.environment.parsed_options.oi_duration

        self.clusters = []

        lat = self.environment.parsed_options.base_lat
        lng = self.environment.parsed_options.base_lng

        time_start = datetime.datetime.now(datetime.UTC)
        time_end = time_start + datetime.timedelta(minutes=60)

        for _ in range(self.environment.parsed_options.cluster_count):
            sub_uuid = str(uuid.uuid4())

            resp = self.client.put(
                f"/dss/v1/subscriptions/{sub_uuid}",
                json={
                    "extents": {
                        "volume": {
                            "outline_circle": {
                                "center": {"lng": lng, "lat": lat},
                                "radius": {"value": self.radius, "units": "M"},
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
                name="/subscriptions/[sub_uuid]",
            )

            if resp.status_code == 200:
                self.clusters.append(
                    Cluster(
                        lng=lng,
                        lat=lat,
                        uuid=sub_uuid,
                        version=resp.json()["subscription"]["version"],
                    )
                )

            # Move latitude approtimatly
            lat += (self.radius * 2) / 111111

    def on_stop(self):
        while self.oi_dict:
            self.task_delete_intent()
        for cluster in self.clusters:
            self.client.delete(
                f"/dss/v1/subscriptions/{cluster.uuid}/{cluster.version}"
            )

    @locust.task(10)
    def task_put_intent(self):
        cluster = random.choice(self.clusters)

        entity_id = uuid.uuid4().hex

        with self.lock:
            key = list(self.known_ovns)

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
                if ovn:
                    self.known_ovns.add(ovn)
        elif resp.status_code == 409:
            try:
                resp_json = resp.json()
                with self.lock:
                    for oi in resp_json.get("missing_operational_intents", []) or []:
                        if "ovn" in oi and oi["ovn"]:
                            self.known_ovns.add(oi["ovn"])
                    for constraint in resp_json.get("missing_constraints", []) or []:
                        if "ovn" in constraint and constraint["ovn"]:
                            self.known_ovns.add(constraint["ovn"])
            except (ValueError, KeyError):
                pass

    @locust.task(1)
    def task_delete_intent(self):
        target_id, target_ovn = self.checkout_intent()
        if not target_id:
            return

        resp = self.client.delete(
            f"/dss/v1/operational_intent_references/{target_id}/{target_ovn}",
            name="/dss/v1/operational_intent_references/[id]/[ovn]",
        )
        if resp.status_code == 200:
            with self.lock:
                if target_ovn in self.known_ovns:
                    self.known_ovns.remove(target_ovn)
        else:
            with self.lock:
                self.oi_dict[target_id] = target_ovn

    def checkout_intent(self):
        with self.lock:
            if not self.oi_dict:
                return None, None
            target_id = random.choice(list(self.oi_dict.keys()))
            target_ovn = self.oi_dict.pop(target_id)
        return target_id, target_ovn
