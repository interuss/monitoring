"""Basic multi-Operation tests:

  - create op1 by uss1
  - create sub2 by uss2
  - use sub2 to create op2 by uss2
  - mutate op1
  - delete op1
  - delete op2
  - delete sub2
"""

import datetime
from typing import Dict, Tuple

from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib import scd
from monitoring.monitorlib.scd import SCOPE_SC
from monitoring.monitorlib.testing import assert_datetimes_are_equal
from monitoring.prober.infrastructure import for_api_versions, register_resource_type
from monitoring.prober.scd import actions


URL_OP1 = "https://example.com/op1/dss"
URL_SUB1 = "https://example.com/subs1/dss"
URL_OP2 = "https://example.com/op2/dss"
URL_SUB2 = "https://example.com/subs2/dss"

OP1_TYPE = register_resource_type(213, "Operational intent 1")
OP2_TYPE = register_resource_type(214, "Operational intent 2")
SUB2_TYPE = register_resource_type(215, "Subscription")


op1_ovn = None
op2_ovn = None

sub2_version = None


def _make_op1_request():
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(minutes=60)
    return {
        "extents": [
            scd.make_vol4(time_start, time_end, 0, 120, scd.make_circle(90, 0, 200))
        ],
        "old_version": 0,
        "state": "Accepted",
        "uss_base_url": URL_OP1,
        "new_subscription": {"uss_base_url": URL_SUB1, "notify_for_constraints": False},
    }


def _make_op2_request():
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(minutes=60)
    return {
        "extents": [
            scd.make_vol4(time_start, time_end, 0, 120, scd.make_circle(89.999, 0, 200))
        ],
        "old_version": 0,
        "state": "Accepted",
        "uss_base_url": URL_OP2,
    }


# Parses `subscribers` response field into Dict[USS base URL, Dict[Subscription ID, Notification index]]
def _parse_subscribers(subscribers: Dict) -> Dict[str, Dict[str, int]]:
    return {
        to_notify["uss_base_url"]: {
            sub["subscription_id"]: sub["notification_index"]
            for sub in to_notify["subscriptions"]
        }
        for to_notify in subscribers
    }


# Parses AirspaceConflictResponse entities into Dict[Operation ID, Operation Reference] +
# Dict[Constraint ID, Constraint Reference]
def _parse_conflicts(conflicts: Dict) -> Tuple[Dict[str, Dict], Dict[str, Dict], set]:
    missing_operational_intents = conflicts.get("missing_operational_intents", [])
    ops = {op["id"]: op for op in missing_operational_intents}
    missing_constraints = conflicts.get("missing_constraints", [])
    constraints = {constraint["id"]: constraint for constraint in missing_constraints}
    ovns = set()
    for entity in missing_constraints + missing_constraints:
        ovn = entity.get("ovn", None)
        if ovn is not None:
            ovns.add(ovn)
    return ops, constraints, ovns


@for_api_versions(scd.API_0_3_17)
def test_ensure_clean_workspace(ids, scd_api, scd_session, scd_session2):
    for op_id, owner in ((ids(OP1_TYPE), scd_session), (ids(OP2_TYPE), scd_session2)):
        actions.delete_operation_if_exists(op_id, owner, scd_api)
    actions.delete_subscription_if_exists(ids(SUB2_TYPE), scd_session2, scd_api)


# Op1 shouldn't exist by ID for USS1 when starting this sequence
# Preconditions: None
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op1_does_not_exist_get_1(ids, scd_api, scd_session, scd_session2):
    resp = scd_session.get("/operational_intent_references/{}".format(ids(OP1_TYPE)))
    assert resp.status_code == 404, resp.content


# Op1 shouldn't exist by ID for USS2 when starting this sequence
# Preconditions: None
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op1_does_not_exist_get_2(ids, scd_api, scd_session2):
    resp = scd_session2.get("/operational_intent_references/{}".format(ids(OP1_TYPE)))
    assert resp.status_code == 404, resp.content


# Op1 shouldn't exist when searching for USS1 when starting this sequence
# Preconditions: None
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op1_does_not_exist_query_1(ids, scd_api, scd_session, scd_session2):
    if scd_session is None:
        return
    time_now = datetime.datetime.utcnow()
    end_time = time_now + datetime.timedelta(hours=1)
    resp = scd_session.post(
        "/operational_intent_references/query",
        json={
            "area_of_interest": scd.make_vol4(
                time_now, end_time, 0, 5000, scd.make_circle(89.999, 180, 300)
            )
        },
    )
    assert resp.status_code == 200, resp.content
    assert ids(OP1_TYPE) not in [
        op["id"] for op in resp.json().get("operational_intent_reference", [])
    ]


# Op1 shouldn't exist when searching for USS2 when starting this sequence
# Preconditions: None
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op1_does_not_exist_query_2(ids, scd_api, scd_session, scd_session2):
    if scd_session2 is None:
        return
    time_now = datetime.datetime.utcnow()
    end_time = time_now + datetime.timedelta(hours=1)
    resp = scd_session2.post(
        "/operational_intent_references/query",
        json={
            "area_of_interest": scd.make_vol4(
                time_now, end_time, 0, 5000, scd.make_circle(89.999, 180, 300)
            )
        },
    )
    assert resp.status_code == 200, resp.content
    assert ids(OP1_TYPE) not in [
        op["id"] for op in resp.json().get("operational_intent_reference", [])
    ]


# Create Op1 normally from USS1 (also creates implicit Subscription)
# Preconditions: None
# Mutations: Operation Op1 created by scd_session user
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_create_op1(ids, scd_api, scd_session, scd_session2):
    req = _make_op1_request()
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP1_TYPE)), json=req
    )
    assert resp.status_code == 201, resp.content

    data = resp.json()
    op = data["operational_intent_reference"]
    assert op["id"] == ids(OP1_TYPE)
    assert op["uss_base_url"] == URL_OP1
    assert op["uss_availability"] == "Unknown"
    assert_datetimes_are_equal(
        op["time_start"]["value"], req["extents"][0]["time_start"]["value"]
    )
    assert_datetimes_are_equal(
        op["time_end"]["value"], req["extents"][0]["time_end"]["value"]
    )
    assert op["version"] == 1
    assert "subscription_id" in op
    assert op["state"] == "Accepted"
    assert op.get("ovn", "")

    # Make sure the implicit Subscription exists when queried separately
    resp = scd_session.get("/subscriptions/{}".format(op["subscription_id"]))
    assert resp.status_code == 200, resp.content

    global op1_ovn
    op1_ovn = op["ovn"]


# Try (unsuccessfully) to delete the implicit Subscription
# Preconditions: Operation Op1 created by scd_session user
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_delete_implicit_sub(ids, scd_api, scd_session, scd_session2):
    if scd_session is None:
        return
    resp = scd_session.get("/operational_intent_references/{}".format(ids(OP1_TYPE)))
    assert resp.status_code == 200, resp.content
    operational_intent_reference = resp.json()["operational_intent_reference"]
    implicit_sub_id = operational_intent_reference["subscription_id"]
    implicit_sub_version = operational_intent_reference["version"]

    resp = scd_session.delete(
        "/subscriptions/{}/{}".format(implicit_sub_id, implicit_sub_version)
    )
    assert resp.status_code == 400, resp.content


# Try (unsuccessfully) to delete Op1 from non-owning USS
# Preconditions: Operation Op1 created by scd_session user
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_delete_op1_by_uss2(ids, scd_api, scd_session, scd_session2):
    resp = scd_session2.delete(
        "/operational_intent_references/{}/{}".format(ids(OP1_TYPE), op1_ovn)
    )
    assert resp.status_code == 403, resp.content


# Try to create Op2 without specifying a valid Subscription
# Preconditions: Operation Op1 created by scd_session user
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_create_op2_no_sub(ids, scd_api, scd_session, scd_session2):
    req = _make_op2_request()
    resp = scd_session2.put(
        "/operational_intent_references/{}".format(ids(OP2_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


# Create a Subscription we can use for Op2
# Preconditions: Operation Op1 created by scd_session user
# Mutations: Subscription Sub2 created by scd_session2 user
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_create_op2sub(ids, scd_api, scd_session, scd_session2):
    if scd_session2 is None:
        return
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(minutes=70)
    req = {
        "extents": scd.make_vol4(
            time_start, time_end, 0, 1000, scd.make_circle(89.999, 0, 250)
        ),
        "uss_base_url": URL_SUB2,
        "notify_for_constraints": False,
    }
    req.update({"notify_for_operational_intents": True})

    resp = scd_session2.put("/subscriptions/{}".format(ids(SUB2_TYPE)), json=req)
    assert resp.status_code == 200, resp.content

    # The Subscription response should mention Op1, but not include its OVN
    data = resp.json()
    ops = data["operational_intent_references"]
    assert len(ops) > 0
    op = [op for op in ops if op["id"] == ids(OP1_TYPE)][0]
    assert op.get("ovn", "") in scd.NO_OVN_PHRASES

    assert data["subscription"]["notification_index"] == 0

    resp = scd_session2.get("/subscriptions/{}".format(ids(SUB2_TYPE)))
    assert resp.status_code == 200, resp.content

    global sub2_version
    sub2_version = data["subscription"]["version"]


# Try (unsuccessfully) to create Op2 with a missing key
# Preconditions:
#   * Operation Op1 created by scd_session user
#   * Subscription Sub2 created by scd_session2 user
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_create_op2_no_key(ids, scd_api, scd_session, scd_session2):
    req = _make_op2_request()
    req["subscription_id"] = ids(SUB2_TYPE)
    resp = scd_session2.put(
        "/operational_intent_references/{}".format(ids(OP2_TYPE)), json=req
    )
    assert resp.status_code == 409, resp.content
    data = resp.json()
    assert "missing_operational_intents" in data, data
    missing_ops, _, _ = _parse_conflicts(data)
    assert ids(OP1_TYPE) in missing_ops


# Create Op2 successfully, referencing the pre-existing Subscription
# Preconditions:
#   * Operation Op1 created by scd_session user
#   * Subscription Sub2 created by scd_session2 user
# Mutations: Operation Op2 created by scd_session2 user
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_create_op2(ids, scd_api, scd_session, scd_session2):
    req = _make_op2_request()
    req["subscription_id"] = ids(SUB2_TYPE)
    req["key"] = [op1_ovn]
    resp = scd_session2.put(
        "/operational_intent_references/{}".format(ids(OP2_TYPE)), json=req
    )
    assert resp.status_code == 201, resp.content

    data = resp.json()
    op = data["operational_intent_reference"]
    assert op["id"] == ids(OP2_TYPE)
    assert op["uss_base_url"] == URL_OP2
    assert_datetimes_are_equal(
        op["time_start"]["value"], req["extents"][0]["time_start"]["value"]
    )
    assert_datetimes_are_equal(
        op["time_end"]["value"], req["extents"][0]["time_end"]["value"]
    )
    assert op["version"] == 1
    assert "subscription_id" in op
    assert op["state"] == "Accepted"
    assert op.get("ovn", "")

    resp = scd_session2.get("/operational_intent_references/{}".format(ids(OP1_TYPE)))
    assert resp.status_code == 200, resp.content
    implicit_sub_id = resp.json()["operational_intent_reference"]["subscription_id"]

    # USS2 should definitely be instructed to notify USS1's implicit Subscription of the new Operation
    subscribers = _parse_subscribers(data.get("subscribers", []))
    assert URL_SUB1 in subscribers, subscribers
    assert implicit_sub_id in subscribers[URL_SUB1], subscribers[URL_SUB1]

    # USS2 should also be instructed to notify USS2's explicit Subscription of the new Operation
    assert URL_SUB2 in subscribers, subscribers
    assert ids(SUB2_TYPE) in subscribers[URL_SUB2], subscribers[URL_SUB2]
    assert subscribers[URL_SUB2][ids(SUB2_TYPE)] == 1

    global op2_ovn
    op2_ovn = op["ovn"]


# Op1 and Op2 should both be visible to USS1, but Op2 shouldn't have an OVN
# Preconditions:
#   * Operation Op1 created by scd_session user
#   * Operation Op2 created by scd_session2 user
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_read_ops_from_uss1(ids, scd_api, scd_session, scd_session2):
    if scd_session is None:
        return
    time_now = datetime.datetime.utcnow()
    end_time = time_now + datetime.timedelta(hours=1)
    resp = scd_session.post(
        "/operational_intent_references/query",
        json={
            "area_of_interest": scd.make_vol4(
                time_now, end_time, 0, 5000, scd.make_circle(89.999, 180, 300)
            )
        },
    )
    assert resp.status_code == 200, resp.content

    ops = {op["id"]: op for op in resp.json().get("operational_intent_references", [])}
    assert ids(OP1_TYPE) in ops
    assert ids(OP2_TYPE) in ops

    ovn1 = ops[ids(OP1_TYPE)].get("ovn", "")
    ovn2 = ops[ids(OP2_TYPE)].get("ovn", "")
    assert ovn1 not in scd.NO_OVN_PHRASES
    assert ovn2 in scd.NO_OVN_PHRASES


# Op1 and Op2 should both be visible to USS2, but Op1 shouldn't have an OVN
# Preconditions:
#   * Operation Op1 created by scd_session user
#   * Operation Op2 created by scd_session2 user
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_read_ops_from_uss2(ids, scd_api, scd_session, scd_session2):
    if scd_session2 is None:
        return
    time_now = datetime.datetime.utcnow()
    end_time = time_now + datetime.timedelta(hours=1)
    resp = scd_session2.post(
        "/operational_intent_references/query",
        json={
            "area_of_interest": scd.make_vol4(
                time_now, end_time, 0, 5000, scd.make_circle(89.999, 180, 300)
            )
        },
    )
    assert resp.status_code == 200, resp.content

    ops = {op["id"]: op for op in resp.json().get("operational_intent_references", [])}
    assert ids(OP1_TYPE) in ops
    assert ids(OP2_TYPE) in ops

    ovn1 = ops[ids(OP1_TYPE)].get("ovn", "")
    ovn2 = ops[ids(OP2_TYPE)].get("ovn", "")
    assert ovn1 in scd.NO_OVN_PHRASES
    assert ovn2 not in scd.NO_OVN_PHRASES


# Try (unsuccessfully) to mutate Op1 with various bad keys
# Preconditions:
#   * Operation Op1 created by scd_session user
#   * Operation Op2 created by scd_session2 user
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_mutate_op1_bad_key(ids, scd_api, scd_session, scd_session2):
    resp = scd_session.get("/operational_intent_references/{}".format(ids(OP1_TYPE)))
    assert resp.status_code == 200, resp.content
    existing_op = resp.json().get("operational_intent_reference", None)
    assert existing_op is not None, resp.content

    old_req = _make_op1_request()
    req = {
        "extents": old_req["extents"],
        "old_version": existing_op["version"],
        "state": "Accepted",
        "uss_base_url": URL_OP1,
        "subscription_id": existing_op["subscription_id"],
    }
    resp = scd_session.put(
        "/operational_intent_references/{}/{}".format(ids(OP1_TYPE), op1_ovn), json=req
    )
    assert resp.status_code == 409, resp.content
    missing_ops, _, _ = _parse_conflicts(resp.json())
    assert ids(OP1_TYPE) in missing_ops
    assert ids(OP2_TYPE) in missing_ops

    req["key"] = [op1_ovn]
    resp = scd_session.put(
        "/operational_intent_references/{}/{}".format(ids(OP1_TYPE), op1_ovn), json=req
    )
    assert resp.status_code == 409, resp.content
    missing_ops, _, ovns = _parse_conflicts(resp.json())
    assert ids(OP2_TYPE) in missing_ops
    assert not (op2_ovn in ovns)
    assert not (op1_ovn in ovns)

    req["key"] = [op2_ovn]
    resp = scd_session.put(
        "/operational_intent_references/{}/{}".format(ids(OP1_TYPE), op1_ovn), json=req
    )
    assert resp.status_code == 409, resp.content
    missing_ops, _, ovns = _parse_conflicts(resp.json())
    assert ids(OP1_TYPE) in missing_ops
    assert not (op2_ovn in ovns)


# Successfully mutate Op1
# Preconditions:
#   * Operation Op1 created by scd_session user
#   * Subscription Sub2 created by scd_session2 user
#   * Operation Op2 created by scd_session2 user
# Mutations: Operation Op1 mutated to second version
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_mutate_op1(ids, scd_api, scd_session, scd_session2):
    resp = scd_session.get("/operational_intent_references/{}".format(ids(OP1_TYPE)))
    assert resp.status_code == 200, resp.content
    existing_op = resp.json().get("operational_intent_reference", None)
    assert existing_op is not None, resp.content

    global op1_ovn

    old_req = _make_op1_request()
    req = {
        "key": [op1_ovn, op2_ovn],
        "extents": old_req["extents"],
        "old_version": existing_op["version"],
        "state": "Accepted",
        "uss_base_url": URL_OP1,
        "subscription_id": existing_op["subscription_id"],
    }
    resp = scd_session.put(
        "/operational_intent_references/{}/{}".format(ids(OP1_TYPE), op1_ovn), json=req
    )
    assert resp.status_code == 200, resp.content

    data = resp.json()
    op = data["operational_intent_reference"]
    assert op["id"] == ids(OP1_TYPE)
    assert op["uss_base_url"] == URL_OP1
    assert op["version"] == 2
    assert op["subscription_id"] == existing_op["subscription_id"]
    assert op["state"] == "Accepted"
    assert op.get("ovn", "")

    # USS1 should definitely be instructed to notify USS2's Subscription of the updated Operation
    subscribers = _parse_subscribers(data.get("subscribers", []))
    assert URL_SUB2 in subscribers, subscribers
    assert ids(SUB2_TYPE) in subscribers[URL_SUB2], subscribers[URL_SUB2]
    assert subscribers[URL_SUB2][ids(SUB2_TYPE)] == 2

    op1_ovn = op["ovn"]


# Try (unsuccessfully) to delete the stand-alone Subscription that Op2 is relying on
# Preconditions:
#   * Subscription Sub2 created by scd_session2 user
#   * Operation Op2 created by scd_session2 user
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_delete_dependent_sub(ids, scd_api, scd_session, scd_session2):
    if scd_session2 is None:
        return
    resp = scd_session2.delete(
        "/subscriptions/{}/{}".format(ids(SUB2_TYPE), sub2_version)
    )
    assert resp.status_code == 400, resp.content


# Mutate the stand-alone Subscription
# Preconditions:
#   * Operation Op1 created by scd_session user
#   * Subscription Sub2 created by scd_session2 user
#   * Operation Op2 created by scd_session2 user
# Mutations: Subscription Sub2 mutated
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_mutate_sub2(ids, scd_api, scd_session, scd_session2):
    if scd_session2 is None:
        return
    time_now = datetime.datetime.utcnow()
    time_start = time_now - datetime.timedelta(minutes=1)
    time_end = time_now + datetime.timedelta(minutes=61)

    # Create a good mutation request
    req = _make_op2_request()
    req["uss_base_url"] = URL_SUB2
    req["extents"] = req["extents"][0]
    del req["state"]
    req["notify_for_constraints"] = False
    req["extents"]["time_start"] = scd.make_time(time_start)
    req["extents"]["time_end"] = scd.make_time(time_end)

    req["notify_for_operational_intents"] = False
    resp = scd_session2.put("/subscriptions/{}".format(ids(SUB2_TYPE)), json=req)
    assert resp.status_code == 400, resp.content
    req["notify_for_operational_intents"] = True

    # Attempt mutation with start time that doesn't cover Op2

    req["extents"]["time_start"] = scd.make_time(
        time_now + datetime.timedelta(minutes=5)
    )
    resp = scd_session2.put(
        "/subscriptions/{}/{}".format(ids(SUB2_TYPE), sub2_version), json=req
    )
    assert resp.status_code == 400, resp.content
    req["extents"]["time_start"] = scd.make_time(time_start)

    # Attempt mutation with end time that doesn't cover Op2
    req["extents"]["time_end"] = scd.make_time(time_now)
    resp = scd_session2.put(
        "/subscriptions/{}/{}".format(ids(SUB2_TYPE), sub2_version), json=req
    )
    assert resp.status_code == 400, resp.content
    req["extents"]["time_end"] = scd.make_time(time_end)

    # # Attempt mutation with minimum altitude that doesn't cover Op2
    req["extents"]["volume"]["altitude_lower"] = scd.make_altitude(10)
    resp = scd_session2.put(
        "/subscriptions/{}/{}".format(ids(SUB2_TYPE), sub2_version), json=req
    )
    assert resp.status_code == 400, resp.content
    req["extents"]["volume"]["altitude_lower"] = scd.make_altitude(0)

    # Attempt mutation with maximum altitude that doesn't cover Op2
    req["extents"]["volume"]["altitude_upper"] = scd.make_altitude(10)
    resp = scd_session2.put(
        "/subscriptions/{}/{}".format(ids(SUB2_TYPE), sub2_version), json=req
    )
    assert resp.status_code == 400, resp.content
    req["extents"]["volume"]["altitude_upper"] = scd.make_altitude(200)

    # # Attempt mutation with outline that doesn't cover Op2
    old_lat = req["extents"]["volume"]["outline_circle"]["center"]["lat"]
    req["extents"]["volume"]["outline_circle"]["center"]["lat"] = 45
    resp = scd_session2.put(
        "/subscriptions/{}/{}".format(ids(SUB2_TYPE), sub2_version), json=req
    )
    assert resp.status_code == 400, resp.content
    req["extents"]["volume"]["outline_circle"]["center"]["lat"] = old_lat

    # Attempt mutation without notifying for Operations
    # Perform a valid mutation
    resp = scd_session2.put(
        "/subscriptions/{}/{}".format(ids(SUB2_TYPE), sub2_version), json=req
    )
    assert resp.status_code == 200, resp.content

    # The Subscription response should mention Op1 and Op2, but not include Op1's OVN
    data = resp.json()
    ops = {op["id"]: op for op in data["operational_intent_references"]}
    assert len(ops) >= 2
    assert ops[ids(OP1_TYPE)].get("ovn", "") in scd.NO_OVN_PHRASES
    assert ops[ids(OP2_TYPE)].get("ovn", "") not in scd.NO_OVN_PHRASES

    assert data["subscription"]["notification_index"] == 2

    # Make sure the Subscription is still retrievable specifically
    resp = scd_session2.get("/subscriptions/{}".format(ids(SUB2_TYPE)))
    assert resp.status_code == 200, resp.content


# Delete Op1
# Preconditions:
#   * Subscription Sub2 created/mutated by scd_session2 user
#   * Operation Op2 created by scd_session2 user
# Mutations: Operation Op1 deleted
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_delete_op1(ids, scd_api, scd_session, scd_session2):
    resp = scd_session.delete(
        "/operational_intent_references/{}/{}".format(ids(OP1_TYPE), op1_ovn)
    )
    assert resp.status_code == 200, resp.content

    data = resp.json()
    op = data["operational_intent_reference"]

    # USS1 should be instructed to notify USS2's Subscription of the deleted Operation
    subscribers = _parse_subscribers(data.get("subscribers", []))
    assert URL_SUB2 in subscribers, subscribers
    assert ids(SUB2_TYPE) in subscribers[URL_SUB2], subscribers[URL_SUB2]
    assert subscribers[URL_SUB2][ids(SUB2_TYPE)] == 3

    resp = scd_session.get("/subscriptions/{}".format(op["subscription_id"]))
    print(resp.content)
    assert resp.status_code == 404, resp.content


# Delete Op2
# Preconditions:
#   * Operation Op1 deleted
#   * Subscription Sub2 created/mutated by scd_session2 user
#   * Operation Op2 created by scd_session2 user
# Mutations: Operation Op2 deleted
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_delete_op2(ids, scd_api, scd_session, scd_session2):
    resp = scd_session2.delete(
        "/operational_intent_references/{}/{}".format(ids(OP2_TYPE), op2_ovn)
    )
    assert resp.status_code == 200, resp.content

    data = resp.json()
    op = data["operational_intent_reference"]
    assert op["subscription_id"] == ids(SUB2_TYPE)

    # USS2 should be instructed to notify Sub2 of the deleted Operation
    subscribers = _parse_subscribers(data.get("subscribers", []))
    assert URL_SUB2 in subscribers, subscribers
    assert ids(SUB2_TYPE) in subscribers[URL_SUB2], subscribers[URL_SUB2]
    assert subscribers[URL_SUB2][ids(SUB2_TYPE)] == 4

    resp = scd_session2.get("/subscriptions/{}".format(ids(SUB2_TYPE)))
    assert resp.status_code == 200, resp.content


# Delete Subscription used to serve Op2
# Preconditions:
#   * Operation Op1 deleted
#   * Subscription Sub2 created/mutated by scd_session2 user
#   * Operation Op2 deleted
# Mutations: Subscription Sub2 deleted
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_delete_sub2(ids, scd_api, scd_session2):
    if scd_session2 is None:
        return
    resp = scd_session2.delete(
        "/subscriptions/{}/{}".format(ids(SUB2_TYPE), sub2_version)
    )
    assert resp.status_code == 200, resp.content


@for_api_versions(scd.API_0_3_17)
def test_final_cleanup(ids, scd_api, scd_session, scd_session2):
    test_ensure_clean_workspace(ids, scd_api, scd_session, scd_session2)
