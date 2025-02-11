"""Basic Operation tests with hundreds of NON-OVERLAPPING operations created CONCURRENTLY.
 The core actions are performed in parallel while others like cleanup, assert response, etc are intended to remain
 sequential.

- make sure operations do not exist with get or query
- create 100 operations concurrently, with has non-overlapping volume4d in 2ds, altitude ranges and time windows.
- get by IDs concurrently
- search by areas concurrently
- mutate operations concurrently
- delete operations concurrently
- confirm deletion by get and query
"""

import asyncio
import datetime
import inspect
import json

from monitoring.monitorlib import scd
from monitoring.monitorlib.geo import Circle
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib.scd import SCOPE_SC
from monitoring.monitorlib.testing import assert_datetimes_are_equal, make_fake_url
from monitoring.prober.infrastructure import (
    IDFactory,
    depends_on,
    for_api_versions,
    register_resource_type,
    resource_type_code_descriptions,
)
from monitoring.prober.scd import actions

BASE_URL = make_fake_url()
# TODO(#742): Increase number of concurrent operations from 20 to 100
OP_TYPES = [
    register_resource_type(110 + i, "Operational intent {}".format(i))
    for i in range(20)
]
GROUP_SIZE = len(OP_TYPES) // 3 + (1 if len(OP_TYPES) % 3 > 0 else 0)
# Semaphore is added to limit the number of simultaneous requests,
# default is 100.
SEMAPHORE = asyncio.Semaphore(10)

ovn_map = {}


def _calculate_lat(idx):
    return -56 - 0.1 * idx


def _make_op_request_with_extents(extents):
    return {
        "extents": [extents],
        "old_version": 0,
        "state": "Accepted",
        "uss_base_url": BASE_URL,
        "new_subscription": {"uss_base_url": BASE_URL, "notify_for_constraints": False},
    }


# Generate request with volumes that cover a circle area that initially centered at (-56, 178)
# The circle's center lat shifts 0.1 degree (11.1 km) per sequential idx change
# The altitude and time window won't change with idx
def _make_op_request_differ_in_2d(idx):
    time_start = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=20)
    time_end = time_start + datetime.timedelta(minutes=60)
    lat = _calculate_lat(idx)

    vol4 = Volume4D.from_values(
        time_start, time_end, 0, 120, Circle.from_meters(lat, 178, 50)
    ).to_f3548v21()
    return _make_op_request_with_extents(vol4)


# Generate request with volumes that cover the circle area that centered at (-56, 178)
# The altitude starts with [0, 19] and increases 20 per sequential idx change
# The 2D area and time window won't change with idx
def _make_op_request_differ_in_altitude(idx):
    time_start = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=20)
    time_end = time_start + datetime.timedelta(minutes=60)
    delta = 20
    alt0 = delta * idx
    alt1 = alt0 + delta - 1

    vol4 = Volume4D.from_values(
        time_start, time_end, alt0, alt1, Circle.from_meters(-56, 178, 50)
    ).to_f3548v21()
    return _make_op_request_with_extents(vol4)


# Generate request with volumes that cover the circle area that centered at (-56, 178), with altitude 0 to 120
# The operation lasts 9 mins and the time window is one after one per sequential idx change
# The 2D area and altitude won't change with idx
def _make_op_request_differ_in_time(idx, time_gap):
    delta = 10
    time_start = (
        datetime.datetime.now(datetime.UTC)
        + time_gap
        + datetime.timedelta(minutes=delta * idx)
    )
    time_end = time_start + datetime.timedelta(minutes=delta - 1)

    vol4 = Volume4D.from_values(
        time_start, time_end, 0, 120, Circle.from_meters(-56, 178, 50)
    ).to_f3548v21()
    return _make_op_request_with_extents(vol4)


# Generate request with non-overlapping operations in volume4d.
# 1/3 operations will be generated with different 2d areas, altitude ranges and time windows respectively
# additional_time_gap is given to keep a time gap between `create` operational_content and `mutate` operational content
# requests, so these two types of requests do not overlap at any time.
def _make_op_request(idx, additional_time_gap=0):
    if idx < GROUP_SIZE:
        req = _make_op_request_differ_in_2d(idx)
        deconflict = "2d"
    elif idx < GROUP_SIZE * 2:
        req = _make_op_request_differ_in_altitude(idx)
        deconflict = "altitude"
    else:
        time_gap = datetime.timedelta(minutes=20 + additional_time_gap)
        req = _make_op_request_differ_in_time(idx, time_gap)
        deconflict = "time"
    extent = req["extents"][0]
    volume = extent["volume"]
    center = volume["outline_circle"]["center"]
    print(
        "{} ({}): ({}, {}) {}-{} {}-{}".format(
            idx,
            deconflict,
            center["lat"],
            center["lng"],
            volume["altitude_lower"]["value"],
            volume["altitude_upper"]["value"],
            extent["time_start"]["value"],
            extent["time_end"]["value"],
        )
    )
    return req


def _intersection(list1, list2):
    return list(set(list1) & set(list2))


async def _put_operation_async(
    req, op_id, scd_session_async, scd_api, create_new: bool
):
    async with SEMAPHORE:
        if scd_api == scd.API_0_3_17:
            if create_new:
                req_url = "/operational_intent_references/{}".format(op_id)
                result = await scd_session_async.put(req_url, data=req), req_url, req
            else:
                req_url = "/operational_intent_references/{}/{}".format(
                    op_id, ovn_map[op_id]
                )
                result = await scd_session_async.put(req_url, data=req), req_url, req
        else:
            raise ValueError("Unsupported SCD API version: {}".format(scd_api))
    return result


async def _get_operation_async(op_id, scd_session_async, scd_api):
    async with SEMAPHORE:
        if scd_api == scd.API_0_3_17:
            result = await scd_session_async.get(
                "/operational_intent_references/{}".format(op_id), scope=SCOPE_SC
            )
        else:
            raise ValueError("Unsupported SCD API version: {}".format(scd_api))
    return result


async def _query_operation_async(idx, scd_session_async, scd_api):
    lat = _calculate_lat(idx)
    req_json = {
        "area_of_interest": Volume4D.from_values(
            None, None, 0, 5000, Circle.from_meters(lat, 178, 12000)
        ).to_f3548v21()
    }
    async with SEMAPHORE:
        if scd_api == scd.API_0_3_17:
            result = await scd_session_async.post(
                "/operational_intent_references/query", json=req_json, scope=SCOPE_SC
            )
        else:
            raise ValueError("Unsupported SCD API version: {}".format(scd_api))
    return result


def _build_mutate_request(idx, op_id, op_map, scd_session, scd_api):
    # GET current op
    if scd_api == scd.API_0_3_17:
        resp = scd_session.get("/operational_intent_references/{}".format(op_id))
        assert resp.status_code == 200, resp.content
        existing_op = resp.json().get("operational_intent_reference", None)
        assert existing_op is not None
        op_map[op_id] = existing_op
    else:
        raise ValueError("Unsupported SCD API version: {}".format(scd_api))

    # mutate requests should be constructed at a good time gap from the create requests.
    additional_time_gap = idx * 10
    req = _make_op_request(idx, additional_time_gap=additional_time_gap)
    req = {
        "key": [existing_op["ovn"]],
        "extents": req["extents"],
        "old_version": existing_op["version"],
        "state": "Activated",
        "uss_base_url": make_fake_url("uss2"),
        "subscription_id": existing_op["subscription_id"],
    }
    return req


async def _delete_operation_async(op_id, scd_session_async, scd_api):
    if scd_api == scd.API_0_3_17:
        result = await scd_session_async.delete(
            "/operational_intent_references/{}/{}".format(op_id, ovn_map[op_id]),
            scope=SCOPE_SC,
        )
    else:
        raise ValueError("Unsupported SCD API version: {}".format(scd_api))
    return result


@for_api_versions(scd.API_0_3_17)
def test_ensure_clean_workspace(ids, scd_api, scd_session):
    for op_id in map(ids, OP_TYPES):
        actions.delete_operation_if_exists(op_id, scd_session, scd_api)


# Preconditions: None
# Mutations: Operations with ids in OP_IDS created by scd_session user
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
def test_create_ops_concurrent(ids, scd_api, scd_session_async):
    start_time = datetime.datetime.now(datetime.UTC)
    assert len(ovn_map) == 0
    op_req_map = {}
    op_resp_map = {}
    for idx, op_id in enumerate(map(ids, OP_TYPES)):
        req = _make_op_request(idx)
        op_req_map[op_id] = req

    # Get operations concurrently
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(
        asyncio.gather(
            *[
                _put_operation_async(req, op_id, scd_session_async, scd_api, True)
                for op_id, req in op_req_map.items()
            ]
        )
    )
    for req_map, resp in zip(op_req_map.items(), results):
        op_id = req_map[0]
        op_resp_map[op_id] = {}
        op_resp_map[op_id]["status_code"] = resp[0][0]
        op_resp_map[op_id]["content"] = resp[0][2]
    for op_id, resp in op_resp_map.items():
        if resp["status_code"] != 201:
            try:
                owner_name, id_code = IDFactory.decode(op_id)
            except ValueError:
                owner_name = "<Unknown owner>"
                id_code = "<Unknown resource ID>"
            print(
                "Error with op_id {}: {}'s {}".format(
                    op_id,
                    owner_name,
                    resource_type_code_descriptions.get(id_code, "<Unknown purpose>"),
                )
            )
            print("=== Request ===")
            print(json.dumps(op_req_map[op_id]))
            print("=== Response ===")
            print(json.dumps(resp["content"]))
            print("=== Missing operational intents ===")
            if "missing_operational_intents" in resp["content"]:
                for missing_op in resp["content"]["missing_operational_intents"]:
                    missing_id = missing_op.get("id", "<Unknown ID>")
                    try:
                        owner_name, id_code = IDFactory.decode(missing_id)
                    except ValueError:
                        owner_name = "<Unknown owner>"
                        id_code = "<Unknown resource ID>"
                    print(
                        "--- Missing op {}: {}'s {}".format(
                            missing_id,
                            owner_name,
                            resource_type_code_descriptions.get(
                                id_code, "<Unknown purpose>"
                            ),
                        )
                    )
                    print("--- Request:")
                    print(json.dumps(op_req_map[missing_id]))
                    print("--- Response:")
                    print(json.dumps(op_resp_map[missing_id]))
        assert resp["status_code"] == 201, resp["content"]
        req = op_req_map[op_id]
        data = resp["content"]
        op = data["operational_intent_reference"]
        assert op["id"] == op_id
        assert op["uss_base_url"] == BASE_URL
        assert_datetimes_are_equal(
            op["time_start"]["value"], req["extents"][0]["time_start"]["value"]
        )
        assert_datetimes_are_equal(
            op["time_end"]["value"], req["extents"][0]["time_end"]["value"]
        )
        assert op["version"] == 1
        assert op["ovn"]
        assert "subscription_id" in op
        ovn_map[op_id] = op["ovn"]
    assert len(ovn_map) == len(OP_TYPES)
    print(
        f"\n{inspect.stack()[0][3]} time_taken: {datetime.datetime.now(datetime.UTC) - start_time}"
    )


# Preconditions: Operations with ids in OP_IDS created by scd_session user
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@depends_on(test_create_ops_concurrent)
def test_get_ops_by_ids_concurrent(ids, scd_api, scd_session_async):
    start_time = datetime.datetime.now(datetime.UTC)
    op_resp_map = {}
    # Get operations concurrently
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(
        asyncio.gather(
            *[
                _get_operation_async(op_id, scd_session_async, scd_api)
                for op_id in map(ids, OP_TYPES)
            ]
        )
    )

    for op_id, resp in zip(map(ids, OP_TYPES), results):
        op_resp_map[op_id] = {}
        op_resp_map[op_id]["status_code"] = resp[0]
        op_resp_map[op_id]["content"] = resp[2]

    for op_id, resp in op_resp_map.items():
        assert resp["status_code"] == 200, resp["content"]

        data = resp["content"]
        op = data["operational_intent_reference"]
        assert op["id"] == op_id
        assert op["uss_base_url"] == BASE_URL
        assert op["version"] == 1
    print(
        f"\n{inspect.stack()[0][3]} time_taken: {datetime.datetime.now(datetime.UTC) - start_time}"
    )


# Preconditions: Operations with ids in OP_IDS created by scd_session user
# Mutations: None
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
@depends_on(test_create_ops_concurrent)
def test_get_ops_by_search_concurrent(ids, scd_api, scd_session_async):
    start_time = datetime.datetime.now(datetime.UTC)
    op_resp_map = {}
    total_found_ids = set()

    # Query operations concurrently
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(
        asyncio.gather(
            *[
                _query_operation_async(idx, scd_session_async, scd_api)
                for idx in range(len(OP_TYPES))
            ]
        )
    )

    for idx, resp in zip(range(len(OP_TYPES)), results):
        op_resp_map[idx] = {}
        op_resp_map[idx]["status_code"] = resp[0]
        op_resp_map[idx]["content"] = resp[2]

    for idx, resp in op_resp_map.items():
        assert resp["status_code"] == 200, resp["content"]
        found_ids = [
            op["id"] for op in resp["content"].get("operational_intent_references", [])
        ]
        total_found_ids.update(found_ids)

    assert len(_intersection(map(ids, OP_TYPES), total_found_ids)) == len(OP_TYPES)
    print(
        f"\n{inspect.stack()[0][3]} time_taken: {datetime.datetime.now(datetime.UTC) - start_time}"
    )


# Preconditions: Operations with ids in OP_IDS created by scd_session user
# Mutations: Operations with ids in OP_IDS mutated to second version
@for_api_versions(scd.API_0_3_17)
@default_scope(SCOPE_SC)
@depends_on(test_create_ops_concurrent)
def test_mutate_ops_concurrent(ids, scd_api, scd_session, scd_session_async):
    start_time = datetime.datetime.now(datetime.UTC)
    op_req_map = {}
    op_resp_map = {}
    op_map = {}

    # Build mutate requests
    for idx, op_id in enumerate(map(ids, OP_TYPES)):
        op_req_map[op_id] = _build_mutate_request(
            idx, op_id, op_map, scd_session, scd_api
        )
    assert len(op_req_map) == len(OP_TYPES)

    # Mutate operations in parallel
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(
        asyncio.gather(
            *[
                _put_operation_async(req, op_id, scd_session_async, scd_api, False)
                for op_id, req in op_req_map.items()
            ]
        )
    )
    print(
        f"\n{inspect.stack()[0][3]} time_taken: {datetime.datetime.now(datetime.UTC) - start_time}"
    )
    for req_map, resp in zip(op_req_map.items(), results):
        op_id = req_map[0]
        op_resp_map[op_id] = {}
        op_resp_map[op_id]["status_code"] = resp[0][0]
        op_resp_map[op_id]["content"] = resp[0][2]

    ovn_map.clear()

    # Check status codes and report all failures together
    ops_with_bad_status = [
        op_id for op_id, resp in op_resp_map.items() if resp["status_code"] != 200
    ]
    if ops_with_bad_status:
        msg = "{} operational intents failed to mutate:\n".format(
            len(ops_with_bad_status)
        )
        msg += "\n".join(
            "{}: {}".format(op_id, op_resp_map[op_id]) for op_id in ops_with_bad_status
        )
        assert False, msg

    # Check details of results
    for op_id, resp in op_resp_map.items():
        existing_op = op_map[op_id]
        assert existing_op
        assert resp["status_code"] == 200, resp["content"]
        data = resp["content"]
        op = data["operational_intent_reference"]
        assert op["id"] == op_id
        assert op["uss_base_url"] == make_fake_url("uss2")
        assert op["version"] == 2
        assert op["subscription_id"] == existing_op["subscription_id"]

        ovn_map[op_id] = op["ovn"]

    assert len(ovn_map) == len(OP_TYPES)


# Preconditions: Operations with ids in OP_IDS mutated to second version
# Mutations: Operations with ids in OP_IDS deleted
@for_api_versions(scd.API_0_3_17)
@depends_on(test_mutate_ops_concurrent)
def test_delete_op_concurrent(ids, scd_api, scd_session_async):
    start_time = datetime.datetime.now(datetime.UTC)
    op_resp_map = {}

    # Delete operations concurrently
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(
        asyncio.gather(
            *[
                _delete_operation_async(op_id, scd_session_async, scd_api)
                for op_id in map(ids, OP_TYPES)
            ]
        )
    )
    for op_id, resp in zip(map(ids, OP_TYPES), results):
        op_resp_map[op_id] = {}
        op_resp_map[op_id]["status_code"] = resp[0]
        op_resp_map[op_id]["content"] = resp[2]

    assert len(op_resp_map) == len(OP_TYPES)

    for resp in op_resp_map.values():
        assert resp["status_code"] == 200, resp["content"]
    print(
        f"\n{inspect.stack()[0][3]} time_taken: {datetime.datetime.now(datetime.UTC) - start_time}"
    )


@for_api_versions(scd.API_0_3_17)
def test_final_cleanup(ids, scd_api, scd_session):
    test_ensure_clean_workspace(ids, scd_api, scd_session)
