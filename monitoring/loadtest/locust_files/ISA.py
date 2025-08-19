#!env/bin/python3

import datetime
import random
import threading
import uuid

import client
from locust import between, task

from monitoring.monitorlib import rid_v1
from monitoring.monitorlib.testing import make_fake_url

VERTICES = [
    {"lng": 130.6205, "lat": -23.6558},
    {"lng": 130.6301, "lat": -23.6898},
    {"lng": 130.6700, "lat": -23.6709},
    {"lng": 130.6466, "lat": -23.6407},
]


class ISA(client.USS):
    wait_time = between(0.01, 1)
    lock = threading.Lock()

    @task(10)
    def create_isa(self):
        time_start = datetime.datetime.now(datetime.UTC)
        time_end = time_start + datetime.timedelta(minutes=60)
        isa_uuid = str(uuid.uuid4())

        resp = self.client.put(
            f"/identification_service_areas/{isa_uuid}",
            json={
                "extents": {
                    "spatial_volume": {
                        "footprint": {
                            "vertices": VERTICES,
                        },
                        "altitude_lo": 20,
                        "altitude_hi": 400,
                    },
                    "time_start": time_start.strftime(rid_v1.DATE_FORMAT),
                    "time_end": time_end.strftime(rid_v1.DATE_FORMAT),
                },
                "flights_url": make_fake_url(),
            },
        )
        if resp.status_code == 200:
            self.isa_dict[isa_uuid] = resp.json()["service_area"]["version"]

    @task(5)
    def update_isa(self):
        target_isa, target_version = self.checkout_isa()
        if not target_isa:
            print("Nothing to pick from isa_dict for UPDATE")
            return

        time_start = datetime.datetime.now(datetime.UTC)
        time_end = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=2)
        resp = self.client.put(
            f"/identification_service_areas/{target_isa}/{target_version}",
            json={
                "extents": {
                    "spatial_volume": {
                        "footprint": {
                            "vertices": VERTICES,
                        },
                        "altitude_lo": 20,
                        "altitude_hi": 400,
                    },
                    "time_start": time_start.strftime(rid_v1.DATE_FORMAT),
                    "time_end": time_end.strftime(rid_v1.DATE_FORMAT),
                },
                "flights_url": make_fake_url(),
            },
        )
        if resp.status_code == 200:
            self.isa_dict[target_isa] = resp.json()["service_area"]["version"]

    @task(100)
    def get_isa(self):
        target_isa = (
            random.choice(list(self.isa_dict.keys())) if self.isa_dict else None
        )
        if not target_isa:
            print("Nothing to pick from isa_dict for GET")
            return
        self.client.get(f"/identification_service_areas/{target_isa}")

    @task(1)
    def delete_isa(self):
        target_isa, target_version = self.checkout_isa()
        if not target_isa:
            print("Nothing to pick from isa_dict for DELETE")
            return
        self.client.delete(
            f"/identification_service_areas/{target_isa}/{target_version}"
        )

    def checkout_isa(self):
        self.lock.acquire()
        target_isa = (
            random.choice(list(self.isa_dict.keys())) if self.isa_dict else None
        )
        target_version = self.isa_dict.pop(target_isa, None)
        self.lock.release()
        return target_isa, target_version

    def on_start(self):
        # insert atleast 1 ISA for update to not fail
        self.create_isa()

    def on_stop(self):
        self.isa_dict = {}
