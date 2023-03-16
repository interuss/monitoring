"""ISA input validation tests:

  - check we can't create the ISA with a huge area
  - check we can't create the ISA with missing fields
  - check we can't create the ISA with a time_start in the past
  - check we can't create the ISA with a time_start after time_end
"""

import datetime

from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib import rid_v1
from monitoring.prober.infrastructure import register_resource_type
from . import common

from uas_standards.astm.f3411.v19.api import OPERATIONS, OperationID
from uas_standards.astm.f3411.v19.constants import Scope

ISA_PATH = OPERATIONS[OperationID.SearchIdentificationServiceAreas].path
ISA_TYPE = register_resource_type(324, "ISA")


def test_ensure_clean_workspace(ids, session_ridv1):
    resp = session_ridv1.get("{}/{}".format(ISA_PATH, ids(ISA_TYPE)), scope=Scope.Read)
    if resp.status_code == 200:
        version = resp.json()["service_area"]["version"]
        resp = session_ridv1.delete(
            "{}/{}/{}".format(ISA_PATH, ids(ISA_TYPE), version), scope=Scope.Write
        )
        assert resp.status_code == 200, resp.content
    elif resp.status_code == 404:
        # As expected.
        pass
    else:
        assert False, resp.content


@default_scope(Scope.Write)
def test_isa_huge_area(ids, session_ridv1):
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(minutes=60)

    resp = session_ridv1.put(
        "{}/{}".format(ISA_PATH, ids(ISA_TYPE)),
        json={
            "extents": {
                "spatial_volume": {
                    "footprint": {
                        "vertices": common.HUGE_VERTICES,
                    },
                    "altitude_lo": 20,
                    "altitude_hi": 400,
                },
                "time_start": time_start.strftime(rid_v1.DATE_FORMAT),
                "time_end": time_end.strftime(rid_v1.DATE_FORMAT),
            },
            "flights_url": "https://example.com/uss/flights",
        },
    )
    assert resp.status_code == 400, resp.content
    assert "too large" in resp.json()["message"]


@default_scope(Scope.Write)
def test_isa_empty_vertices(ids, session_ridv1):
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(minutes=60)

    resp = session_ridv1.put(
        "{}/{}".format(ISA_PATH, ids(ISA_TYPE)),
        json={
            "extents": {
                "spatial_volume": {
                    "footprint": {
                        "vertices": [],
                    },
                    "altitude_lo": 20,
                    "altitude_hi": 400,
                },
                "time_start": time_start.strftime(rid_v1.DATE_FORMAT),
                "time_end": time_end.strftime(rid_v1.DATE_FORMAT),
            },
            "flights_url": "https://example.com/uss/flights",
        },
    )
    assert resp.status_code == 400, resp.content
    assert "Missing or malformed required extents" in resp.json()["message"]


@default_scope(Scope.Write)
def test_isa_missing_footprint(ids, session_ridv1):
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(minutes=60)

    resp = session_ridv1.put(
        "{}/{}".format(ISA_PATH, ids(ISA_TYPE)),
        json={
            "extents": {
                "spatial_volume": {
                    "altitude_lo": 20,
                    "altitude_hi": 400,
                },
                "time_start": time_start.strftime(rid_v1.DATE_FORMAT),
                "time_end": time_end.strftime(rid_v1.DATE_FORMAT),
            },
            "flights_url": "https://example.com/uss/flights",
        },
    )
    assert resp.status_code == 400, resp.content
    assert "Missing or malformed required extents" in resp.json()["message"]


@default_scope(Scope.Write)
def test_isa_missing_spatial_volume(ids, session_ridv1):
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(minutes=60)

    resp = session_ridv1.put(
        "{}/{}".format(ISA_PATH, ids(ISA_TYPE)),
        json={
            "extents": {
                "time_start": time_start.strftime(rid_v1.DATE_FORMAT),
                "time_end": time_end.strftime(rid_v1.DATE_FORMAT),
            },
            "flights_url": "https://example.com/uss/flights",
        },
    )
    assert resp.status_code == 400, resp.content
    assert "Missing or malformed required extents" in resp.json()["message"]


@default_scope(Scope.Write)
def test_isa_missing_extents(ids, session_ridv1):
    resp = session_ridv1.put(
        "{}/{}".format(ISA_PATH, ids(ISA_TYPE)),
        json={
            "flights_url": "https://example.com/uss/flights",
        },
    )
    assert resp.status_code == 400, resp.content
    assert "Missing or malformed required extents" in resp.json()["message"]


@default_scope(Scope.Write)
def test_isa_start_time_in_past(ids, session_ridv1):
    time_start = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
    time_end = time_start + datetime.timedelta(minutes=60)

    resp = session_ridv1.put(
        "{}/{}".format(ISA_PATH, ids(ISA_TYPE)),
        json={
            "extents": {
                "spatial_volume": {
                    "footprint": {
                        "vertices": common.VERTICES,
                    },
                    "altitude_lo": 20,
                    "altitude_hi": 400,
                },
                "time_start": time_start.strftime(rid_v1.DATE_FORMAT),
                "time_end": time_end.strftime(rid_v1.DATE_FORMAT),
            },
            "flights_url": "https://example.com/uss/flights",
        },
    )
    assert resp.status_code == 400, resp.content
    assert (
        "IdentificationServiceArea time_start must not be in the past"
        in resp.json()["message"]
    )


@default_scope(Scope.Write)
def test_isa_start_time_after_time_end(ids, session_ridv1):
    time_start = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    time_end = time_start - datetime.timedelta(minutes=5)

    resp = session_ridv1.put(
        "{}/{}".format(ISA_PATH, ids(ISA_TYPE)),
        json={
            "extents": {
                "spatial_volume": {
                    "footprint": {
                        "vertices": common.VERTICES,
                    },
                    "altitude_lo": 20,
                    "altitude_hi": 400,
                },
                "time_start": time_start.strftime(rid_v1.DATE_FORMAT),
                "time_end": time_end.strftime(rid_v1.DATE_FORMAT),
            },
            "flights_url": "https://example.com/uss/flights",
        },
    )
    assert resp.status_code == 400, resp.content
    assert (
        "IdentificationServiceArea time_end must be after time_start"
        in resp.json()["message"]
    )


@default_scope(Scope.Write)
def test_isa_not_on_earth(ids, session_ridv1):
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(minutes=60)

    resp = session_ridv1.put(
        "{}/{}".format(ISA_PATH, ids(ISA_TYPE)),
        json={
            "extents": {
                "spatial_volume": {
                    "footprint": {
                        "vertices": [
                            {"lat": 130.6205, "lng": -23.6558},
                            {"lat": 130.6301, "lng": -23.6898},
                            {"lat": 130.6700, "lng": -23.6709},
                            {"lat": 130.6466, "lng": -23.6407},
                        ],
                    },
                    "altitude_lo": 20,
                    "altitude_hi": 400,
                },
                "time_start": time_start.strftime(rid_v1.DATE_FORMAT),
                "time_end": time_end.strftime(rid_v1.DATE_FORMAT),
            },
            "flights_url": "https://example.com/uss/flights",
        },
    )
    assert resp.status_code == 400, resp.content
