"""Basic Constraint tests:

  - make sure the Constraint doesn't exist with get or query
  - create the Constraint with a 60 minute length
  - get by ID
  - search with earliest_time and latest_time
  - mutate
  - delete
"""

import datetime

import pytest

from monitoring.monitorlib import scd
from monitoring.monitorlib.geo import Circle
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib.scd import (
    SCOPE_AA,
    SCOPE_CM,
    SCOPE_CM_SA,
    SCOPE_CP,
    SCOPE_SC,
)
from monitoring.monitorlib.testing import assert_datetimes_are_equal, make_fake_url
from monitoring.prober.infrastructure import (
    depends_on,
    for_api_versions,
    register_resource_type,
)
from monitoring.prober.scd import actions

BASE_URL = make_fake_url()
CONSTRAINT_TYPE = register_resource_type(1, "Single constraint")


def _make_c1_request():
    time_start = datetime.datetime.now(datetime.UTC)
    time_end = time_start + datetime.timedelta(minutes=60)
    return {
        "extents": [
            Volume4D.from_values(
                time_start, time_end, 0, 120, Circle.from_meters(-56, 178, 50)
            ).to_f3548v21()
        ],
        "old_version": 0,
        "uss_base_url": BASE_URL,
    }


def test_ensure_clean_workspace(ids, scd_api, scd_session, scd_session_cm):
    if not scd_session_cm:
        pytest.skip("SCD auth1 not enabled for constraint management")
    actions.delete_constraint_reference_if_exists(
        ids(CONSTRAINT_TYPE), scd_session, scd_api
    )


@depends_on(test_ensure_clean_workspace)
def test_constraint_does_not_exist_get(ids, scd_api, scd_session):
    auths = (SCOPE_CM, SCOPE_CP)

    for scope in auths:
        resp = scd_session.get(
            "/constraint_references/{}".format(ids(CONSTRAINT_TYPE)), scope=scope
        )
        assert resp.status_code == 404, resp.content


@depends_on(test_ensure_clean_workspace)
def test_constraint_does_not_exist_query(ids, scd_api, scd_session):
    if scd_session is None:
        return
    time_now = datetime.datetime.now(datetime.UTC)

    auths = (SCOPE_CM, SCOPE_CP)

    for scope in auths:
        resp = scd_session.post(
            "/constraint_references/query",
            json={
                "area_of_interest": Volume4D.from_values(
                    time_now, time_now, 0, 5000, Circle.from_meters(-56, 178, 300)
                ).to_f3548v21()
            },
            scope=scope,
        )
        assert resp.status_code == 200, resp.content
        assert ids(CONSTRAINT_TYPE) not in [
            constraint["id"]
            for constraint in resp.json().get("constraint_references", [])
        ]


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_CM)
@depends_on(test_ensure_clean_workspace)
def test_create_constraint_single_extent(ids, scd_api, scd_session):
    req = _make_c1_request()
    req["extents"] = req["extents"][0]
    resp = scd_session.put(
        "/constraint_references/{}".format(ids(CONSTRAINT_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_CM)
@depends_on(test_ensure_clean_workspace)
def test_create_constraint_missing_time_start(ids, scd_api, scd_session):
    req = _make_c1_request()
    del req["extents"][0]["time_start"]
    resp = scd_session.put(
        "/constraint_references/{}".format(ids(CONSTRAINT_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_CM)
@depends_on(test_ensure_clean_workspace)
def test_create_constraint_missing_time_end(ids, scd_api, scd_session):
    req = _make_c1_request()
    del req["extents"][0]["time_end"]
    resp = scd_session.put(
        "/constraint_references/{}".format(ids(CONSTRAINT_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@depends_on(test_ensure_clean_workspace)
def test_create_constraint(ids, scd_api, scd_session):
    id = ids(CONSTRAINT_TYPE)
    req = _make_c1_request()

    resp = scd_session.put(
        "/constraint_references/{}".format(id), json=req, scope=SCOPE_SC
    )
    assert resp.status_code == 403, resp.content

    resp = scd_session.put(
        "/constraint_references/{}".format(id), json=req, scope=SCOPE_CP
    )
    assert resp.status_code == 403, resp.content

    resp = scd_session.put(
        "/constraint_references/{}".format(id), json=req, scope=SCOPE_CM
    )
    assert resp.status_code == 201, resp.content

    data = resp.json()
    constraint = data["constraint_reference"]
    assert constraint["id"] == id
    assert constraint["uss_base_url"] == BASE_URL
    assert constraint["uss_availability"] == "Unknown"
    assert_datetimes_are_equal(
        constraint["time_start"]["value"], req["extents"][0]["time_start"]["value"]
    )
    assert_datetimes_are_equal(
        constraint["time_end"]["value"], req["extents"][0]["time_end"]["value"]
    )
    assert constraint["version"] == 1


@for_api_versions(scd.API_0_3_17)
@depends_on(test_create_constraint)
def test_get_constraint_by_id(ids, scd_api, scd_session):
    id = ids(CONSTRAINT_TYPE)

    auths = (SCOPE_CM, SCOPE_CP)

    for scope in auths:
        resp = scd_session.get("/constraint_references/{}".format(id), scope=scope)
        assert resp.status_code == 200, resp.content

        data = resp.json()
        constraint = data["constraint_reference"]
        assert constraint["id"] == id
        assert constraint["uss_base_url"] == BASE_URL
        assert constraint["uss_availability"] == "Unknown"
        assert constraint["version"] == 1


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_CM)
@depends_on(test_create_constraint)
def test_get_constraint_by_search_missing_params(scd_api, scd_session):
    resp = scd_session.post("/constraint_references/query")
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@depends_on(test_create_constraint)
def test_get_constraint_by_search(ids, scd_api, scd_session):
    auths = (SCOPE_CM, SCOPE_CP)

    for scope in auths:
        resp = scd_session.post(
            "/constraint_references/query",
            json={
                "area_of_interest": Volume4D.from_values(
                    None, None, 0, 5000, Circle.from_meters(-56, 178, 300)
                ).to_f3548v21()
            },
            scope=scope,
        )
        assert resp.status_code == 200, resp.content
        assert ids(CONSTRAINT_TYPE) in [
            x["id"] for x in resp.json().get("constraint_references", [])
        ]


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_CM)
@depends_on(test_create_constraint)
def test_get_constraint_by_search_earliest_time_included(ids, scd_api, scd_session):
    earliest_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=59)
    resp = scd_session.post(
        "/constraint_references/query",
        json={
            "area_of_interest": Volume4D.from_values(
                earliest_time, None, 0, 5000, Circle.from_meters(-56, 178, 300)
            ).to_f3548v21()
        },
    )
    assert resp.status_code == 200, resp.content
    assert ids(CONSTRAINT_TYPE) in [
        x["id"] for x in resp.json()["constraint_references"]
    ]


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_CM)
@depends_on(test_create_constraint)
def test_get_constraint_by_search_earliest_time_excluded(ids, scd_api, scd_session):
    earliest_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=61)
    resp = scd_session.post(
        "/constraint_references/query",
        json={
            "area_of_interest": Volume4D.from_values(
                earliest_time, None, 0, 5000, Circle.from_meters(-56, 178, 300)
            ).to_f3548v21()
        },
    )
    assert resp.status_code == 200, resp.content
    assert ids(CONSTRAINT_TYPE) not in [
        x["id"] for x in resp.json()["constraint_references"]
    ]


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_CM)
@depends_on(test_create_constraint)
def test_get_constraint_by_search_latest_time_included(ids, scd_api, scd_session):
    latest_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=1)
    resp = scd_session.post(
        "/constraint_references/query",
        json={
            "area_of_interest": Volume4D.from_values(
                None, latest_time, 0, 5000, Circle.from_meters(-56, 178, 300)
            ).to_f3548v21()
        },
    )
    assert resp.status_code == 200, resp.content
    assert ids(CONSTRAINT_TYPE) in [
        x["id"] for x in resp.json()["constraint_references"]
    ]


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_CM)
@depends_on(test_create_constraint)
def test_get_constraint_by_search_latest_time_excluded(ids, scd_api, scd_session):
    latest_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=1)
    resp = scd_session.post(
        "/constraint_references/query",
        json={
            "area_of_interest": Volume4D.from_values(
                None, latest_time, 0, 5000, Circle.from_meters(-56, 178, 300)
            ).to_f3548v21()
        },
    )
    assert resp.status_code == 200, resp.content
    assert ids(CONSTRAINT_TYPE) not in [
        x["id"] for x in resp.json()["constraint_references"]
    ]


@for_api_versions(scd.API_0_3_17)
@depends_on(test_create_constraint)
def test_mutate_constraint(ids, scd_api, scd_session):
    id = ids(CONSTRAINT_TYPE)
    # GET current constraint
    resp = scd_session.get("/constraint_references/{}".format(id), scope=SCOPE_CP)
    assert resp.status_code == 200, resp.content
    existing_constraint = resp.json().get("constraint_reference", None)
    assert existing_constraint is not None

    req = _make_c1_request()
    req = {
        "key": [existing_constraint["ovn"]],
        "extents": req["extents"],
        "old_version": existing_constraint["version"],
        "uss_base_url": make_fake_url("uss2"),
    }

    ovn = existing_constraint["ovn"]

    resp = scd_session.put(
        "/constraint_references/{}/{}".format(id, ovn), json=req, scope=SCOPE_SC
    )
    assert resp.status_code == 403, "ovn:{}\nresponse: {}".format(ovn, resp.content)

    resp = scd_session.put(
        "/constraint_references/{}/{}".format(id, ovn), json=req, scope=SCOPE_CP
    )
    assert resp.status_code == 403, "ovn:{}\nresponse: {}".format(ovn, resp.content)

    resp = scd_session.put(
        "/constraint_references/{}/{}".format(id, ovn), json=req, scope=SCOPE_CM_SA
    )
    assert resp.status_code == 403, "ovn:{}\nresponse: {}".format(ovn, resp.content)

    resp = scd_session.put(
        "/constraint_references/{}/{}".format(id, ovn), json=req, scope=SCOPE_AA
    )
    assert resp.status_code == 403, "ovn:{}\nresponse: {}".format(ovn, resp.content)

    resp = scd_session.put(
        "/constraint_references/{}/{}".format(id, ovn), json=req, scope=SCOPE_CM
    )
    assert resp.status_code == 200, "ovn:{}\nresponse: {}".format(ovn, resp.content)

    data = resp.json()
    constraint = data["constraint_reference"]
    assert constraint["id"] == id
    assert constraint["uss_base_url"] == make_fake_url("uss2")
    assert constraint["uss_availability"] == "Unknown"
    assert constraint["version"] == 2


@for_api_versions(scd.API_0_3_17)
@depends_on(test_mutate_constraint)
def test_delete_constraint(ids, scd_api, scd_session):
    id = ids(CONSTRAINT_TYPE)

    resp = scd_session.get("/constraint_references/{}".format(id), scope=SCOPE_CP)
    assert resp.status_code == 200, resp.content
    existing_constraint = resp.json().get("constraint_reference", None)
    assert existing_constraint is not None

    req = _make_c1_request()
    req = {
        "key": [existing_constraint["ovn"]],
        "extents": req["extents"],
        "old_version": existing_constraint["version"],
        "uss_base_url": make_fake_url("uss2"),
    }

    ovn = existing_constraint["ovn"]

    resp = scd_session.delete(
        "/constraint_references/{}/{}".format(id, ovn), json=req, scope=SCOPE_SC
    )
    assert resp.status_code == 403, "ovn:{}\nresponse: {}".format(ovn, resp.content)

    resp = scd_session.delete(
        "/constraint_references/{}/{}".format(id, ovn), json=req, scope=SCOPE_CP
    )
    assert resp.status_code == 403, "ovn:{}\nresponse: {}".format(ovn, resp.content)

    resp = scd_session.delete(
        "/constraint_references/{}/{}".format(id, ovn), json=req, scope=SCOPE_CM_SA
    )
    assert resp.status_code == 403, "ovn:{}\nresponse: {}".format(ovn, resp.content)

    resp = scd_session.delete(
        "/constraint_references/{}/{}".format(id, ovn), json=req, scope=SCOPE_AA
    )
    assert resp.status_code == 403, "ovn:{}\nresponse: {}".format(ovn, resp.content)

    resp = scd_session.delete(
        "/constraint_references/{}/{}".format(id, ovn), json=req, scope=SCOPE_CM
    )
    assert resp.status_code == 200, "ovn:{}\nresponse: {}".format(ovn, resp.content)


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_CM)
@depends_on(test_delete_constraint)
def test_get_deleted_constraint_by_id(ids, scd_api, scd_session):
    resp = scd_session.get("/constraint_references/{}".format(ids(CONSTRAINT_TYPE)))
    assert resp.status_code == 404, resp.content


# Preconditions: Constraint SIMPLE_CONSTRAINT deleted
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_CM)
@depends_on(test_delete_constraint)
def test_get_deleted_constraint_by_search(ids, scd_api, scd_session):
    resp = scd_session.post(
        "/constraint_references/query",
        json={
            "area_of_interest": Volume4D.from_values(
                None, None, 0, 5000, Circle.from_meters(-56, 178, 300)
            ).to_f3548v21()
        },
    )
    assert resp.status_code == 200, resp.content
    assert ids(CONSTRAINT_TYPE) not in [
        x["id"] for x in resp.json()["constraint_references"]
    ]


@for_api_versions(scd.API_0_3_17)
def test_final_cleanup(ids, scd_api, scd_session, scd_session_cm):
    test_ensure_clean_workspace(ids, scd_api, scd_session, scd_session_cm)
