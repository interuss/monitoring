"""Subscription update validation tests:

  - make sure Operation doesn't exist by ID
  - create Operation with implicit Subscription
  - make sure implicit Subscription is created
  - try mutate Subscription by shrinking 2d area which does not cover Operation
  - try mutate Subscription by shrinking altitude range which does not cover Operation
  - try mutate Subscription by shrinking time range  which does not cover Operation
  - mutate Subscription with the same 2d area
  - delete Operation
  - delete Subscription
"""

import datetime

from monitoring.monitorlib import scd
from monitoring.monitorlib.geo import Circle
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib.scd import SCOPE_SC
from monitoring.monitorlib.testing import assert_datetimes_are_equal, make_fake_url
from monitoring.prober.infrastructure import (
    depends_on,
    for_api_versions,
    register_resource_type,
)
from monitoring.prober.scd import actions

BASE_URL = make_fake_url()
OP_TYPE = register_resource_type(221, "Operational intent")
sub_id = None


def _make_op_req():
    time_start = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=20)
    time_end = time_start + datetime.timedelta(minutes=60)
    return {
        "extents": [
            Volume4D.from_values(
                time_start, time_end, 0, 1000, Circle.from_meters(-56, 178, 500)
            ).to_f3548v21()
        ],
        "old_version": 0,
        "state": "Accepted",
        "uss_base_url": BASE_URL,
        "new_subscription": {"uss_base_url": BASE_URL, "notify_for_constraints": False},
    }


def _make_sub_req(time_start, time_end, alt_start, alt_end, radius, scd_api):
    req = {
        "extents": Volume4D.from_values(
            time_start,
            time_end,
            alt_start,
            alt_end,
            Circle.from_meters(-56, 178, radius),
        ).to_f3548v21(),
        "old_version": 0,
        "uss_base_url": BASE_URL,
        "notify_for_constraints": False,
    }
    req["notify_for_operational_intents"] = True
    return req


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_ensure_clean_workspace(ids, scd_api, scd_session):
    actions.delete_subscription_if_exists(ids(OP_TYPE), scd_session, scd_api)


# Create operation normally (also creates implicit Subscription)
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_create_op(ids, scd_api, scd_session):
    entity_name = "operational_intent_reference"
    req = _make_op_req()
    resp = scd_session.put("/{}s/{}".format(entity_name, ids(OP_TYPE)), json=req)
    assert resp.status_code == 201, resp.content

    data = resp.json()
    op = data[entity_name]
    assert op["id"] == ids(OP_TYPE)
    assert op["uss_base_url"] == BASE_URL
    assert_datetimes_are_equal(
        op["time_start"]["value"], req["extents"][0]["time_start"]["value"]
    )
    assert_datetimes_are_equal(
        op["time_end"]["value"], req["extents"][0]["time_end"]["value"]
    )
    assert op["version"] == 1
    assert "subscription_id" in op

    assert op["state"] == "Accepted"

    # Make sure the implicit Subscription exists when queried separately
    global sub_id
    sub_id = op["subscription_id"]

    resp = scd_session.get("/subscriptions/{}".format(sub_id))
    assert resp.status_code == 200, resp.content


# Try to mutate subscription by shrinking its 2d area
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
@depends_on(test_create_op)
def test_mutate_sub_shrink_2d(scd_api, scd_session):
    # GET current sub before mutation
    resp = scd_session.get("/subscriptions/{}".format(sub_id))
    assert resp.status_code == 200, resp.content
    existing_sub = resp.json().get("subscription", None)
    assert existing_sub is not None

    time_start = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=20)
    time_end = time_start + datetime.timedelta(minutes=60)
    req = _make_sub_req(time_start, time_end, 0, 1000, 50, scd_api)
    req["notify_for_constraints"] = True

    resp = scd_session.put(
        "/subscriptions/{}/{}".format(sub_id, existing_sub["version"]), json=req
    )
    assert resp.status_code == 400, resp.content


# Try to mutate subscription by shrinking its altitude range
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
@depends_on(test_create_op)
def test_mutate_sub_shrink_altitude(scd_api, scd_session):
    # GET current sub before mutation
    resp = scd_session.get("/subscriptions/{}".format(sub_id))
    assert resp.status_code == 200, resp.content
    existing_sub = resp.json().get("subscription", None)
    assert existing_sub is not None

    time_start = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=20)
    time_end = time_start + datetime.timedelta(minutes=60)
    req = _make_sub_req(time_start, time_end, 200, 1000, 500, scd_api)
    req["notify_for_constraints"] = True

    resp = scd_session.put(
        "/subscriptions/{}/{}".format(sub_id, existing_sub["version"]), json=req
    )
    assert resp.status_code == 400, resp.content


# Try to mutate subscription by shrinking its time range
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
@depends_on(test_create_op)
def test_mutate_sub_shrink_time(scd_api, scd_session):
    # GET current sub before mutation
    resp = scd_session.get("/subscriptions/{}".format(sub_id))
    assert resp.status_code == 200, resp.content
    existing_sub = resp.json().get("subscription", None)
    assert existing_sub is not None

    time_start = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=20)
    time_end = time_start + datetime.timedelta(minutes=40)
    req = _make_sub_req(time_start, time_end, 0, 1000, 500, scd_api)
    req["notify_for_constraints"] = True

    resp = scd_session.put(
        "/subscriptions/{}/{}".format(sub_id, existing_sub["version"]), json=req
    )
    assert resp.status_code == 400, resp.content


# Mutate sub, with the same 2d area
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
@depends_on(test_create_op)
def test_mutate_sub_not_shrink(scd_api, scd_session):
    # GET current sub before mutation
    resp = scd_session.get("/subscriptions/{}".format(sub_id))
    assert resp.status_code == 200, resp.content
    existing_sub = resp.json().get("subscription", None)
    assert existing_sub is not None

    time_start = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=20)
    time_end = time_start + datetime.timedelta(minutes=60)
    req = _make_sub_req(time_start, time_end, 0, 1000, 500, scd_api)
    req["notify_for_constraints"] = True

    resp = scd_session.put(
        "/subscriptions/{}/{}".format(sub_id, existing_sub["version"]), json=req
    )
    assert resp.status_code == 200, resp.content

    data = resp.json()
    assert_datetimes_are_equal(
        data["subscription"]["time_start"]["value"],
        req["extents"]["time_start"]["value"],
    )
    assert_datetimes_are_equal(
        data["subscription"]["time_end"]["value"], req["extents"]["time_end"]["value"]
    )


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
@depends_on(test_mutate_sub_not_shrink)
def test_delete_op(ids, scd_api, scd_session):
    resp = scd_session.get("/operational_intent_references/{}".format(ids(OP_TYPE)))
    assert resp.status_code == 200, resp.content
    ovn = resp.json()["operational_intent_reference"]["ovn"]
    resp = scd_session.delete(
        "/operational_intent_references/{}/{}".format(ids(OP_TYPE), ovn)
    )
    assert resp.status_code == 200, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
@depends_on(test_delete_op)
def test_get_deleted_op_by_id(ids, scd_api, scd_session):
    resp = scd_session.get("/operational_intent_references/{}".format(ids(OP_TYPE)))
    assert resp.status_code == 404, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
@depends_on(test_create_op)
def test_delete_sub(scd_api, scd_session):
    resp = scd_session.get("/subscriptions/{}".format(sub_id))
    assert resp.status_code == 200, resp.content
    version = resp.json()["subscription"]["version"]
    resp = scd_session.delete("/subscriptions/{}/{}".format(sub_id, version))
    assert resp.status_code == 200, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
@depends_on(test_create_op)
def test_get_deleted_sub_by_id(scd_api, scd_session):
    resp = scd_session.get("/subscriptions/{}".format(sub_id))
    assert resp.status_code == 404, resp.content


@for_api_versions(scd.API_0_3_17)
def test_final_cleanup(ids, scd_api, scd_session):
    test_ensure_clean_workspace(ids, scd_api, scd_session)
