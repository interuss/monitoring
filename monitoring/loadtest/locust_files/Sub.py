#!env/bin/python3
import datetime
import random
import threading
import uuid

import client
from locust import between, task

from monitoring.monitorlib import rid_v1
from monitoring.monitorlib.testing import make_fake_url


class Sub(client.USS):
    wait_time = between(0.01, 1)
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

    @task(100)
    def create_sub(self):
        time_start = datetime.datetime.now(datetime.UTC)
        time_end = time_start + datetime.timedelta(minutes=60)
        sub_uuid = str(uuid.uuid4())

        resp = self.client.put(
            f"/subscriptions/{sub_uuid}",
            json={
                "extents": {
                    "spatial_volume": {
                        "footprint": {
                            "vertices": self.gen_vertices(),
                        },
                        "altitude_lo": 20,
                        "altitude_hi": 400,
                    },
                    "time_start": time_start.strftime(rid_v1.DATE_FORMAT),
                    "time_end": time_end.strftime(rid_v1.DATE_FORMAT),
                },
                "callbacks": {"identification_service_area_url": make_fake_url()},
            },
            name="/subscriptions/[sub_uuid]",
        )
        if resp.status_code == 200:
            self.sub_dict[sub_uuid] = resp.json()["subscription"]["version"]

    @task(20)
    def get_sub(self):
        target_sub = (
            random.choice(list(self.sub_dict.keys())) if self.sub_dict else None
        )
        if not target_sub:
            print("Nothing to pick from sub_dict for GET")
            return
        self.client.get(
            f"/subscriptions/{target_sub}",
            name="/subscriptions/[target_sub]",
        )

    @task(50)
    def update_sub(self):
        target_sub, target_version = self.checkout_sub()
        if not target_sub:
            print("Nothing to pick from sub_dict for UPDATE")
            return

        time_start = datetime.datetime.now(datetime.UTC)
        time_end = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=2)
        resp = self.client.put(
            f"/subscriptions/{target_sub}/{target_version}",
            json={
                "extents": {
                    "spatial_volume": {
                        "footprint": {
                            "vertices": self.gen_vertices(),
                        },
                        "altitude_lo": 20,
                        "altitude_hi": 400,
                    },
                    "time_start": time_start.strftime(rid_v1.DATE_FORMAT),
                    "time_end": time_end.strftime(rid_v1.DATE_FORMAT),
                },
                "callbacks": {"identification_service_area_url": make_fake_url()},
            },
            name="/subscriptions/[target_sub]/[target_version]",
        )
        if resp.status_code == 200:
            self.sub_dict[target_sub] = resp.json()["subscription"]["version"]

    @task(5)
    def delete_sub(self):
        target_sub, target_version = self.checkout_sub()
        if not target_sub:
            print("Nothing to pick from sub_dict for DELETE")
            return
        self.client.delete(
            f"/subscriptions/{target_sub}/{target_version}",
            name="/subscriptions/[target_sub]/[target_version]",
        )

    def checkout_sub(self):
        self.lock.acquire()
        target_sub = (
            random.choice(list(self.sub_dict.keys())) if self.sub_dict else None
        )
        target_version = self.sub_dict.pop(target_sub, None)
        self.lock.release()
        return target_sub, target_version

    def on_start(self):
        # Insert atleast 1 Sub for update to not fail
        self.create_sub()

    def on_stop(self):
        self.sub_dict = {}
