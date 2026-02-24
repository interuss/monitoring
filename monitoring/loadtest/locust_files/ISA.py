import argparse
import datetime
import random
import threading
import uuid

import client
import locust
from utils import format_time

VERTICES = [
    {"lng": 130.6205, "lat": -23.6558},
    {"lng": 130.6301, "lat": -23.6898},
    {"lng": 130.6700, "lat": -23.6709},
    {"lng": 130.6466, "lat": -23.6407},
]


@locust.events.init_command_line_parser.add_listener
def init_parser(parser: argparse.ArgumentParser):
    """Setup config params, populated by locust.conf."""

    parser.add_argument(
        "--uss-base-url",
        type=str,
        help="Base URL of the USS",
        required=True,
    )


class ISA(client.USS):
    wait_time = locust.between(0.01, 1)
    lock = threading.Lock()

    @locust.task(10)
    def create_isa(self):
        time_start = datetime.datetime.now(datetime.UTC)
        time_end = time_start + datetime.timedelta(minutes=60)
        isa_uuid = str(uuid.uuid4())

        resp = self.client.put(
            f"/rid/v2/dss/identification_service_areas/{isa_uuid}",
            json={
                "extents": {
                    "volume": {
                        "outline_polygon": {
                            "vertices": VERTICES,
                        },
                        "altitude_lower": {
                            "value": 20,
                            "reference": "W84",
                            "units": "M",
                        },
                        "altitude_upper": {
                            "value": 400,
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
                "uss_base_url": self.uss_base_url,
            },
            name="/identification_service_areas/[isa_uuid]",
        )
        if resp.status_code == 200:
            with self.lock:
                self.isa_dict[isa_uuid] = resp.json()["service_area"]["version"]

    @locust.task(5)
    def update_isa(self):
        target_isa, target_version = self.checkout_isa()
        if not target_isa:
            print("Nothing to pick from isa_dict for UPDATE")
            return

        time_start = datetime.datetime.now(datetime.UTC)
        time_end = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=2)
        resp = self.client.put(
            f"/rid/v2/dss/identification_service_areas/{target_isa}/{target_version}",
            json={
                "extents": {
                    "volume": {
                        "outline_polygon": {
                            "vertices": VERTICES,
                        },
                        "altitude_lower": {
                            "value": 20,
                            "reference": "W84",
                            "units": "M",
                        },
                        "altitude_upper": {
                            "value": 400,
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
                "uss_base_url": self.uss_base_url,
            },
            name="/identification_service_areas/[target_isa]/[target_version]",
        )
        if resp.status_code == 200:
            with self.lock:
                self.isa_dict[target_isa] = resp.json()["service_area"]["version"]

    @locust.task(100)
    def get_isa(self):
        if not self.isa_dict:
            print("Nothing to pick from isa_dict for GET")
            return
        with self.lock:
            target_isa = random.choice(list(self.isa_dict.keys()))
        self.client.get(
            f"/rid/v2/dss/identification_service_areas/{target_isa}",
            name="/identification_service_areas/[target_isa]",
        )

    @locust.task(1)
    def delete_isa(self):
        target_isa, target_version = self.checkout_isa()
        if not target_isa:
            print("Nothing to pick from isa_dict for DELETE")
            return
        self.client.delete(
            f"/rid/v2/dss/identification_service_areas/{target_isa}/{target_version}",
            name="/identification_service_areas/[target_isa]/[target_version]",
        )

    def checkout_isa(self):
        with self.lock:
            if not self.isa_dict:
                return None, None
            target_isa = random.choice(list(self.isa_dict.keys()))
            target_version = self.isa_dict.pop(target_isa, None)
        return target_isa, target_version

    def on_start(self):
        self.uss_base_url = self.environment.parsed_options.uss_base_url
        # insert atleast 1 ISA for update to not fail
        self.create_isa()

    def on_stop(self):
        while self.isa_dict:  # Drain ISAs
            self.delete_isa()
