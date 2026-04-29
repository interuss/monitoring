import argparse
import random
import uuid

import client
import locust
from geo_utils import create_random_flight_path_volume


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
        self.lat = self.environment.parsed_options.area_lat
        self.lng = self.environment.parsed_options.area_lng
        self.radius = self.environment.parsed_options.area_radius
        self.max_flight_distance = self.environment.parsed_options.max_flight_distance
        self.oi_duration = self.environment.parsed_options.oi_duration

    def on_stop(self):
        while self.oi_dict:
            self.task_delete_intent()

    @locust.task(10)
    def task_put_intent(self):
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
                self.lat,
                self.lng,
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
