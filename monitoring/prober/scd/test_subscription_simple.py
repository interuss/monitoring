"""Basic strategic conflict detection Subscription tests:

- make sure Subscription doesn't exist by ID
- make sure Subscription doesn't exist by search
- create the Subscription with a 60 minute expiry
- get by ID
- get by searching a circular area
- delete
- make sure Subscription can't be found by ID
- make sure Subscription can't be found by search
"""

# MIGRATION NOTE: has been migrated to uss_qualifier under subscription_simple

import datetime

from uas_standards.astm.f3548.v21 import api

from monitoring.monitorlib import scd
from monitoring.monitorlib.geo import Circle
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib.scd import SCOPE_SC
from monitoring.monitorlib.testing import assert_datetimes_are_equal, make_fake_url
from monitoring.prober.infrastructure import for_api_versions, register_resource_type
from monitoring.prober.scd import actions

SUB_TYPE = register_resource_type(220, "Subscription")


@for_api_versions(scd.API_0_3_17)
def test_ensure_clean_workspace(ids, scd_api, scd_session):
    actions.delete_subscription_if_exists(ids(SUB_TYPE), scd_session, scd_api)


def _make_sub1_req(scd_api):
    time_start = datetime.datetime.now(datetime.UTC)
    time_end = time_start + datetime.timedelta(minutes=60)
    req = {
        "extents": Volume4D.from_values(
            time_start, time_end, 0, 1000, Circle.from_meters(12, -34, 300)
        ).to_f3548v21(),
        "uss_base_url": make_fake_url(),
        "notify_for_constraints": False,
    }
    req.update({"notify_for_operational_intents": True})
    return req


def _check_sub1(data, sub_id, scd_api):
    assert data["subscription"]["id"] == sub_id
    assert ("notification_index" not in data["subscription"]) or (
        data["subscription"]["notification_index"] == 0
    )
    assert data["subscription"]["uss_base_url"] == make_fake_url()
    assert data["subscription"]["time_start"]["format"] == api.TimeFormat.RFC3339
    assert data["subscription"]["time_end"]["format"] == api.TimeFormat.RFC3339
    assert ("notify_for_constraints" not in data["subscription"]) or (
        data["subscription"]["notify_for_constraints"] == False
    )
    assert ("implicit_subscription" not in data["subscription"]) or (
        data["subscription"]["implicit_subscription"] == False
    )
    assert data["subscription"]["notify_for_operational_intents"] == True
    assert ("dependent_operational_intents" not in data["subscription"]) or len(
        data["subscription"]["dependent_operational_intents"]
    ) == 0


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_sub_does_not_exist_get(ids, scd_api, scd_session):
    if scd_session is None:
        return
    resp = scd_session.get("/subscriptions/{}".format(ids(SUB_TYPE)))
    assert resp.status_code == 404, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_sub_does_not_exist_query(ids, scd_api, scd_session):
    if scd_session is None:
        return
    resp = scd_session.post(
        "/subscriptions/query",
        json={
            "area_of_interest": Volume4D.from_values(
                None, None, 0, 5000, Circle.from_meters(12, -34, 300)
            ).to_f3548v21()
        },
    )
    assert resp.status_code == 200, resp.content
    assert ids(SUB_TYPE) not in [
        sub["id"] for sub in resp.json().get("subscriptions", [])
    ]


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_create_sub(ids, scd_api, scd_session):
    if scd_session is None:
        return
    req = _make_sub1_req(scd_api)
    resp = scd_session.put("/subscriptions/{}".format(ids(SUB_TYPE)), json=req)
    assert resp.status_code == 200, resp.content

    data = resp.json()
    assert_datetimes_are_equal(
        data["subscription"]["time_start"]["value"],
        req["extents"]["time_start"]["value"],
    )
    assert_datetimes_are_equal(
        data["subscription"]["time_end"]["value"], req["extents"]["time_end"]["value"]
    )
    _check_sub1(data, ids(SUB_TYPE), scd_api)
    assert "constraint_references" not in data
    assert isinstance(data["operational_intent_references"], list)


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_get_sub_by_id(ids, scd_api, scd_session):
    if scd_session is None:
        return
    resp = scd_session.get("/subscriptions/{}".format(ids(SUB_TYPE)))
    assert resp.status_code == 200, resp.content

    data = resp.json()
    _check_sub1(data, ids(SUB_TYPE), scd_api)


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_get_sub_by_search(ids, scd_api, scd_session):
    if scd_session is None:
        return
    time_now = datetime.datetime.now(datetime.UTC)
    resp = scd_session.post(
        "/subscriptions/query",
        json={
            "area_of_interest": Volume4D.from_values(
                time_now, time_now, 0, 120, Circle.from_meters(12.00001, -34.00001, 50)
            ).to_f3548v21()
        },
    )
    if resp.status_code != 200:
        print(resp.content)
    assert resp.status_code == 200, resp.content
    assert ids(SUB_TYPE) in [x["id"] for x in resp.json()["subscriptions"]]


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_mutate_sub(ids, scd_api, scd_session):
    if scd_session is None:
        return

    # GET current sub1 before mutation
    resp = scd_session.get("/subscriptions/{}".format(ids(SUB_TYPE)))
    assert resp.status_code == 200, resp.content
    existing_sub = resp.json().get("subscription", None)
    assert existing_sub is not None

    req = _make_sub1_req(scd_api)
    req["notify_for_constraints"] = True
    req["notify_for_operational_intents"] = False

    if scd_api == scd.API_0_3_17:
        resp = scd_session.put(
            "/subscriptions/{}/{}".format(ids(SUB_TYPE), existing_sub["version"]),
            json=req,
        )
    else:
        raise NotImplementedError("Unsupported API version {}".format(scd_api))
    assert resp.status_code == 200, resp.content

    data = resp.json()
    assert_datetimes_are_equal(
        data["subscription"]["time_start"]["value"],
        req["extents"]["time_start"]["value"],
    )
    assert_datetimes_are_equal(
        data["subscription"]["time_end"]["value"], req["extents"]["time_end"]["value"]
    )
    assert isinstance(data["constraint_references"], list)
    assert "operational_intent_references" not in data


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_delete_sub(ids, scd_api, scd_session):
    if scd_session is None:
        return
    if scd_api == scd.API_0_3_17:
        resp = scd_session.get("/subscriptions/{}".format(ids(SUB_TYPE)))
        assert resp.status_code == 200, resp.content
        resp = scd_session.delete(
            "/subscriptions/{}/{}".format(
                ids(SUB_TYPE), resp.json()["subscription"]["version"]
            )
        )
    else:
        raise NotImplementedError("Unsupported API version {}".format(scd_api))
    assert resp.status_code == 200, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_get_deleted_sub_by_id(ids, scd_api, scd_session):
    if scd_session is None:
        return
    resp = scd_session.get("/subscriptions/{}".format(ids(SUB_TYPE)))
    assert resp.status_code == 404, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_get_deleted_sub_by_search(ids, scd_api, scd_session):
    if scd_session is None:
        return
    time_now = datetime.datetime.now(datetime.UTC)
    resp = scd_session.post(
        "/subscriptions/query",
        json={
            "area_of_interest": Volume4D.from_values(
                time_now, time_now, 0, 120, Circle.from_meters(12.00001, -34.00001, 50)
            ).to_f3548v21()
        },
    )
    assert resp.status_code == 200, resp.content
    assert ids(SUB_TYPE) not in [x["id"] for x in resp.json()["subscriptions"]]


@for_api_versions(scd.API_0_3_17)
def test_final_cleanup(ids, scd_api, scd_session):
    test_ensure_clean_workspace(ids, scd_api, scd_session)
