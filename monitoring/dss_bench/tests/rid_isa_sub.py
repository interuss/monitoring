"""ISA load identical to rid_isa, but with ONE subscription covering the test
area pre-created on each DSS before the load starts (exercises the DSS
subscriber-matching path on every ISA write). Shares RidIsa's action/setup.

RID areas are capped at a 7 km diagonal, so the test operates in one small zone
covered by a single subscription rather than literally the whole world.
"""

import random
import uuid

import requests

from monitoring.dss_bench.auth import issue_token
from monitoring.dss_bench.tests.rid_isa import RidIsa, _extents

# Small zone the ISAs operate in, and a slightly larger covering polygon for the
# subscription (both well under the 7 km diagonal limit).
_ISA_AREA = [
    {"lng": 1.000, "lat": 1.000},
    {"lng": 1.000, "lat": 1.010},
    {"lng": 1.010, "lat": 1.010},
    {"lng": 1.010, "lat": 1.000},
]
_COVER_AREA = [
    {"lng": 0.995, "lat": 0.995},
    {"lng": 0.995, "lat": 1.015},
    {"lng": 1.015, "lat": 1.015},
    {"lng": 1.015, "lat": 0.995},
]


class RidIsaWithSub(RidIsa):
    name = "rid_isa_sub"
    default = True

    def __init__(self):
        self.areas = [_ISA_AREA]
        self._rng = random.Random()

    def prepare(self, cfg, targets: list[tuple[str, str]]) -> None:
        for base_url, audience in targets:
            token = issue_token(
                cfg.oauth_token_endpoint, cfg.oauth_sub, audience, self.scopes
            )
            session = requests.Session()
            session.headers["Authorization"] = f"Bearer {token}"
            body = {"extents": _extents(_COVER_AREA), "uss_base_url": base_url}
            resp = session.put(
                f"{base_url}/rid/v2/dss/subscriptions/{uuid.uuid4()}",
                json=body,
                timeout=10,
            )
            resp.raise_for_status()
