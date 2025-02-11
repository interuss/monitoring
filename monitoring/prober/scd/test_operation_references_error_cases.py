"""Operation References corner cases error tests:"""

import json
import uuid

import arrow
import yaml

from monitoring.monitorlib import scd
from monitoring.monitorlib.geotemporal import Volume4D, Volume4DCollection
from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib.scd import SCOPE_SC
from monitoring.prober.infrastructure import for_api_versions, register_resource_type
from monitoring.prober.scd import actions

OP_TYPE = register_resource_type(342, "Primary operational intent")
OP_TYPE2 = register_resource_type(343, "Conflicting operational intent")


@for_api_versions(scd.API_0_3_17)
def test_ensure_clean_workspace(ids, scd_api, scd_session):
    for op_id in (ids(OP_TYPE), ids(OP_TYPE2)):
        actions.delete_operation_if_exists(op_id, scd_session, scd_api)


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_ref_area_too_large(scd_api, scd_session):
    with open("./scd/resources/op_ref_area_too_large.json", "r") as f:
        req = json.load(f)
    resp = scd_session.post("/operational_intent_references/query", json=req)
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_ref_start_end_times_past(scd_api, scd_session):
    with open("./scd/resources/op_ref_start_end_times_past.json", "r") as f:
        req = json.load(f)
    resp = scd_session.post("/operational_intent_references/query", json=req)
    # It is ok (and useful) to query for past Operations that may not yet have
    # been explicitly deleted.  This is unlike remote ID where ISAs are
    # auto-removed from the perspective of the client immediately after their end
    # time.
    assert resp.status_code == 200, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_ref_incorrect_units(scd_api, scd_session):
    with open("./scd/resources/op_ref_incorrect_units.json", "r") as f:
        req = json.load(f)
    resp = scd_session.post("/operational_intent_references/query", json=req)
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_ref_incorrect_altitude_ref(scd_api, scd_session):
    with open("./scd/resources/op_ref_incorrect_altitude_ref.json", "r") as f:
        req = json.load(f)
    resp = scd_session.post("/operational_intent_references/query", json=req)
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_uss_base_url_non_tls(ids, scd_api, scd_session):
    with open("./scd/resources/op_uss_base_url_non_tls.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_bad_subscription_id(ids, scd_api, scd_session):
    with open("./scd/resources/op_bad_subscription.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_bad_subscription_id_random(ids, scd_api, scd_session):
    with open("./scd/resources/op_bad_subscription.json", "r") as f:
        req = json.load(f)
        req["subscription_id"] = uuid.uuid4().hex
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_new_and_existing_subscription(ids, scd_api, scd_session):
    with open("./scd/resources/op_new_and_existing_subscription.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_end_time_past(ids, scd_api, scd_session):
    with open("./scd/resources/op_end_time_past.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_already_exists(ids, scd_api, scd_session):
    with open("./scd/resources/op_request_1.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 201, resp.content
    ovn = resp.json()["operational_intent_reference"]["ovn"]

    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 409, resp.content

    # Delete operation
    resp = scd_session.delete(
        "/operational_intent_references/{}/{}".format(ids(OP_TYPE), ovn)
    )
    assert resp.status_code == 200, resp.content

    # Verify deletion
    resp = scd_session.get("/operational_intent_references/{}".format(ids(OP_TYPE)))
    assert resp.status_code == 404, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_400_version1(ids, scd_api, scd_session):
    with open("./scd/resources/op_400_version1.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_bad_state_version0(ids, scd_api, scd_session):
    with open("./scd/resources/op_bad_state_version0.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_bad_lat_lon_range(ids, scd_api, scd_session):
    with open("./scd/resources/op_bad_lat_lon_range.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_area_too_large_put(ids, scd_api, scd_session):
    with open("./scd/resources/op_area_too_large_put.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_bad_time_format(ids, scd_api, scd_session):
    with open("./scd/resources/op_bad_time_format.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_bad_volume(ids, scd_api, scd_session):
    with open("./scd/resources/op_bad_volume.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_repeated_requests(ids, scd_api, scd_session):
    with open("./scd/resources/op_request_1.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 201, resp.content
    ovn = resp.json()["operational_intent_reference"]["ovn"]

    print(resp.json()["operational_intent_reference"]["ovn"])
    assert "operational_intent_reference" in resp.json(), resp.content
    assert "ovn" in resp.json()["operational_intent_reference"], resp.content
    ovn = resp.json()["operational_intent_reference"]["ovn"]

    with open("./scd/resources/op_request_1.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 409, resp.content

    # Delete operation
    resp = scd_session.delete(
        "/operational_intent_references/{}/{}".format(ids(OP_TYPE), ovn)
    )
    assert resp.status_code == 200, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_op_invalid_id(scd_api, scd_session):
    with open("./scd/resources/op_request_1.json", "r") as f:
        req = json.load(f)
    resp = scd_session.put("/operational_intent_references/not_uuid_format", json=req)
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_missing_conflicted_operation(ids, scd_api, scd_session):
    # Emplace the initial version of Operation 1
    with open("./scd/resources/op_missing_initial.yaml", "r") as f:
        req = yaml.full_load(f)
    extents = Volume4DCollection.from_f3548v21(req["extents"])
    dt = arrow.utcnow().datetime - extents.time_start.datetime
    req["extents"] = extents.offset_times(dt).to_f3548v21()
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE)), json=req
    )
    assert resp.status_code == 201, resp.content
    ovn1a = resp.json()["operational_intent_reference"]["ovn"]
    sub_id = resp.json()["operational_intent_reference"]["subscription_id"]

    # Emplace the pre-existing Operation that conflicted in the original observation
    with open("./scd/resources/op_missing_preexisting_unknown.yaml", "r") as f:
        req = yaml.full_load(f)
    extents = Volume4DCollection.from_f3548v21(req["extents"])
    req["extents"] = extents.offset_times(dt).to_f3548v21()
    req["key"] = [ovn1a]
    resp = scd_session.put(
        "/operational_intent_references/{}".format(ids(OP_TYPE2)), json=req
    )
    assert resp.status_code == 201, resp.content

    # Attempt to update Operation 1 without OVN for the pre-existing Operation
    with open("./scd/resources/op_missing_update.json", "r") as f:
        req = json.load(f)
    req["extents"] = (
        Volume4DCollection.from_f3548v21(req["extents"]).offset_times(dt).to_f3548v21()
    )
    req["key"] = [ovn1a]
    req["subscription_id"] = sub_id
    resp = scd_session.put(
        "/operational_intent_references/{}/{}".format(ids(OP_TYPE), ovn1a), json=req
    )
    assert resp.status_code == 409, resp.content

    # checking entity conflicts
    conflicts = []
    data = resp.json()
    assert "missing_operational_intents" in data
    assert ids(OP_TYPE2) in [
        intent["id"] for intent in data["missing_operational_intents"]
    ], resp.content

    # Perform an area-based query on the area occupied by Operation 1
    with open("./scd/resources/op_missing_query.json", "r") as f:
        req = json.load(f)
    req["area_of_interest"] = (
        Volume4D.from_f3548v21(req["area_of_interest"]).offset_time(dt).to_f3548v21()
    )
    resp = scd_session.post("/operational_intent_references/query", json=req)
    assert resp.status_code == 200, resp.content
    ops = [op["id"] for op in resp.json()["operational_intent_references"]]
    assert ids(OP_TYPE) in ops, resp.content

    # ids(OP_ID2) not expected here because its ceiling is <575m whereas query floor is
    # >591m.
    assert ids(OP_TYPE2) not in ops, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_big_operation_search(scd_api, scd_session):
    with open("./scd/resources/op_big_operation.json", "r") as f:
        req = json.load(f)
    aoi = Volume4D.from_f3548v21(req["area_of_interest"])
    dt = arrow.utcnow().datetime - aoi.time_start.datetime
    req["area_of_interest"] = aoi.offset_time(dt).to_f3548v21()
    resp = scd_session.post("/operational_intent_references/query", json=req)
    assert resp.status_code == 400, resp.content


@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_clean_up(ids, scd_api, scd_session):
    for op_id in (ids(OP_TYPE), ids(OP_TYPE2)):
        resp = scd_session.get(
            "/operational_intent_references/{}".format(op_id), scope=SCOPE_SC
        )
        if resp.status_code == 200:
            # only the owner of the subscription can delete a operation reference.
            assert "operational_intent_reference" in resp.json(), resp.content
            assert "ovn" in resp.json()["operational_intent_reference"], resp.content
            ovn = resp.json()["operational_intent_reference"]["ovn"]
            resp = scd_session.delete(
                "/operational_intent_references/{}/{}".format(op_id, ovn),
                scope=SCOPE_SC,
            )
            assert resp.status_code == 200, resp.content
        elif resp.status_code == 404:
            # As expected.
            pass
        else:
            assert False, resp.content


@for_api_versions(scd.API_0_3_17)
def test_final_cleanup(ids, scd_api, scd_session):
    test_ensure_clean_workspace(ids, scd_api, scd_session)
