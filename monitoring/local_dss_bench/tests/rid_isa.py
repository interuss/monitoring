"""Insert then delete a RID v2 ISA in one of N predefined random areas."""

import datetime
import random
import uuid

import requests

from monitoring.local_dss_bench.tests.base import BenchTest


def _random_area() -> list[dict]:
    base_lng = random.randint(0, 179)
    base_lat = random.randint(-90, 88)
    return [
        {"lng": base_lng + 0.6205, "lat": base_lat + 0.6558},
        {"lng": base_lng + 0.6301, "lat": base_lat + 0.6898},
        {"lng": base_lng + 0.6700, "lat": base_lat + 0.6709},
        {"lng": base_lng + 0.6466, "lat": base_lat + 0.6407},
    ]


def _extents(vertices: list[dict]) -> dict:
    start = datetime.datetime.now(datetime.UTC)
    end = start + datetime.timedelta(minutes=60)
    return {
        "volume": {
            "outline_polygon": {"vertices": vertices},
            "altitude_lower": {"value": 20, "reference": "W84", "units": "M"},
            "altitude_upper": {"value": 400, "reference": "W84", "units": "M"},
        },
        "time_start": {"value": start.isoformat(), "format": "RFC3339"},
        "time_end": {"value": end.isoformat(), "format": "RFC3339"},
    }


class RidIsa(BenchTest):
    name = "rid_isa"
    scopes = ["rid.service_provider", "rid.display_provider"]
    default = True

    def __init__(self, n_areas: int = 100):
        self.areas = [_random_area() for _ in range(n_areas)]
        self._rng = random.Random()

    def setup(self, session: requests.Session, base_url: str) -> None:
        self._rng = random.Random()  # distinct per worker, avoids lockstep choices

    def action(self, session: requests.Session, base_url: str) -> None:
        isa_id = str(uuid.uuid4())
        body = {
            "extents": _extents(self._rng.choice(self.areas)),
            "uss_base_url": base_url,
        }

        put = session.put(
            f"{base_url}/rid/v2/dss/identification_service_areas/{isa_id}",
            json=body,
            timeout=10,
        )
        put.raise_for_status()
        version = put.json()["service_area"]["version"]

        delete = session.delete(
            f"{base_url}/rid/v2/dss/identification_service_areas/{isa_id}/{version}",
            timeout=10,
        )
        delete.raise_for_status()
