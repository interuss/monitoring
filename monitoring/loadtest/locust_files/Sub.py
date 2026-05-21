import argparse
import datetime
import random
import threading
import uuid

import client
import locust
from utils import format_time


@locust.events.init_command_line_parser.add_listener
def init_parser(parser: argparse.ArgumentParser):
    """Setup config params, populated by locust.conf."""

    parser.add_argument(
        "--uss-base-url",
        type=str,
        help="Base URL of the USS",
        required=True,
    )


class Sub(client.USS):
    wait_time = locust.between(0.01, 1)
    lock = threading.Lock()

    def gen_vertices(self):
        base_lng = random.randint(0, 180)
        base_lat = random.randint(-90, 90)
        return [
            {"lng": base_lng + 0.6205, "lat": base_lat + 0.6558},
            {"lng": base_lng + 0.6301, "lat": base_lat + 0.6898},
            {"lng": base_lng + 0.6700, "lat": base_lat + 0.6709},
            {"lng": base_lng + 0.6466, "lat": base_lat + 0.6407},
        ]

    @locust.task(100)
    def create_sub(self):
        time_start = datetime.datetime.now(datetime.UTC)
        time_end = time_start + datetime.timedelta(minutes=60)
        sub_uuid = str(uuid.uuid4())

        resp = self.client.put(
            f"/rid/v2/dss/subscriptions/{sub_uuid}",
            json={
                "extents": {
                    "volume": {
                        "outline_polygon": {
                            "vertices": self.gen_vertices(),
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
            name="/subscriptions/[sub_uuid]",
        )
        if resp.status_code == 200:
            with self.lock:
                self.sub_dict[sub_uuid] = resp.json()["subscription"]["version"]

    @locust.task(20)
    def get_sub(self):
        with self.lock:
            if not self.sub_dict:
                print("Nothing to pick from sub_dict for GET")
                return
            target_sub = random.choice(list(self.sub_dict.keys()))
        self.client.get(
            f"/rid/v2/dss/subscriptions/{target_sub}",
            name="/subscriptions/[target_sub]",
        )

    @locust.task(50)
    def update_sub(self):
        target_sub, target_version = self.checkout_sub()
        if not target_sub:
            print("Nothing to pick from sub_dict for UPDATE")
            return

        time_start = datetime.datetime.now(datetime.UTC)
        time_end = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=2)
        resp = self.client.put(
            f"/rid/v2/dss/subscriptions/{target_sub}/{target_version}",
            json={
                "extents": {
                    "volume": {
                        "outline_polygon": {
                            "vertices": self.gen_vertices(),
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
            name="/subscriptions/[target_sub]/[target_version]",
        )
        if resp.status_code == 200:
            with self.lock:
                self.sub_dict[target_sub] = resp.json()["subscription"]["version"]

    @locust.task(5)
    def delete_sub(self):
        target_sub, target_version = self.checkout_sub()
        if not target_sub:
            print("Nothing to pick from sub_dict for DELETE")
            return
        self.client.delete(
            f"/rid/v2/dss/subscriptions/{target_sub}/{target_version}",
            name="/subscriptions/[target_sub]/[target_version]",
        )

    def checkout_sub(self):
        with self.lock:
            if not self.sub_dict:
                return None, None
            target_sub = random.choice(list(self.sub_dict.keys()))
            target_version = self.sub_dict.pop(target_sub, None)
        return target_sub, target_version

    def on_start(self):
        self.uss_base_url = self.environment.parsed_options.uss_base_url
        # Insert atleast 1 Sub for update to not fail
        self.create_sub()

    def on_stop(self):
        while self.sub_dict:  # Drain subscriptions
            self.delete_sub()
