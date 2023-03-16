"""Subscription input validation tests:
  - check we can't create too many SUBS (common.MAX_SUBS_PER_AREA)
  - check we can't create the SUB with a huge area
  - check we can't create the SUB with missing fields
  - check we can't create the SUB with a time_start in the past
  - check we can't create the SUB with a time_start after time_end
"""
import datetime

from uas_standards.astm.f3411.v22a.api import OPERATIONS, OperationID
from uas_standards.astm.f3411.v22a.constants import (
    Scope,
    NetDSSMaxSubscriptionPerArea,
    NetDSSMaxSubscriptionDurationHours,
)


from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib import rid_v2
from monitoring.prober.infrastructure import register_resource_type
from . import common


SUBSCRIPTION_PATH = OPERATIONS[OperationID.SearchSubscriptions].path
SUB_TYPE = register_resource_type(350, "Subscription")
MULTI_SUB_TYPES = [
    register_resource_type(351 + i, "Subscription limit Subscription {}".format(i))
    for i in range(11)
]
BASE_URL = "https://example.com/rid/v2"


def test_ensure_clean_workspace(ids, session_ridv2):
    resp = session_ridv2.get(
        "{}/{}".format(SUBSCRIPTION_PATH, ids(SUB_TYPE)), scope=Scope.DisplayProvider
    )
    if resp.status_code == 200:
        version = resp.json()["subscription"]["version"]
        resp = session_ridv2.delete(
            "{}/{}/{}".format(SUBSCRIPTION_PATH, ids(SUB_TYPE), version),
            scope=Scope.DisplayProvider,
        )
        assert resp.status_code == 200, resp.content
    elif resp.status_code == 404:
        # As expected.
        pass
    else:
        assert False, resp.content


@default_scope(Scope.DisplayProvider)
def test_create_sub_empty_vertices(ids, session_ridv2):
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(seconds=10)

    resp = session_ridv2.put(
        "{}/{}".format(SUBSCRIPTION_PATH, ids(SUB_TYPE)),
        json={
            "extents": {
                "volume": {
                    "outline_polygon": {
                        "vertices": [],
                    },
                    "altitude_lower": rid_v2.make_altitude(20),
                    "altitude_upper": rid_v2.make_altitude(400),
                },
                "time_start": rid_v2.make_time(time_start),
                "time_end": rid_v2.make_time(time_end),
            },
            "uss_base_url": BASE_URL,
        },
    )
    assert resp.status_code == 400, resp.content


@default_scope(Scope.DisplayProvider)
def test_create_sub_missing_outline_polygon(ids, session_ridv2):
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(seconds=10)

    resp = session_ridv2.put(
        "{}/{}".format(SUBSCRIPTION_PATH, ids(SUB_TYPE)),
        json={
            "extents": {
                "volume": {
                    "altitude_lower": rid_v2.make_altitude(20),
                    "altitude_upper": rid_v2.make_altitude(400),
                },
                "time_start": rid_v2.make_time(time_start),
                "time_end": rid_v2.make_time(time_end),
            },
            "uss_base_url": BASE_URL,
        },
    )
    assert resp.status_code == 400, resp.content


@default_scope(Scope.DisplayProvider)
def test_create_sub_with_huge_area(ids, session_ridv2):
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(seconds=10)

    resp = session_ridv2.put(
        "{}/{}".format(SUBSCRIPTION_PATH, ids(SUB_TYPE)),
        json={
            "extents": {
                "volume": {
                    "outline_polygon": {
                        "vertices": common.HUGE_VERTICES,
                    },
                    "altitude_lower": rid_v2.make_altitude(20),
                    "altitude_upper": rid_v2.make_altitude(400),
                },
                "time_start": rid_v2.make_time(time_start),
                "time_end": rid_v2.make_time(time_end),
            },
            "uss_base_url": BASE_URL,
        },
    )
    assert resp.status_code == 400, resp.content


@default_scope(Scope.DisplayProvider)
def test_create_too_many_subs(ids, session_ridv2):
    """ASTM Compliance Test: DSS0050_MAX_SUBS_PER_AREA."""
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(seconds=30)

    # create 1 more than the max allowed Subscriptions per area
    versions = []
    for index in range(NetDSSMaxSubscriptionPerArea + 1):
        resp = session_ridv2.put(
            "{}/{}".format(SUBSCRIPTION_PATH, ids(MULTI_SUB_TYPES[index])),
            json={
                "extents": {
                    "volume": {
                        "outline_polygon": {
                            "vertices": [
                                {
                                    "lat": 37.440,
                                    "lng": -131.745,
                                },
                                {
                                    "lat": 37.459,
                                    "lng": -131.745,
                                },
                                {
                                    "lat": 37.459,
                                    "lng": -131.706,
                                },
                                {
                                    "lat": 37.440,
                                    "lng": -131.706,
                                },
                            ],
                        },
                        "altitude_lower": rid_v2.make_altitude(20),
                        "altitude_upper": rid_v2.make_altitude(400),
                    },
                    "time_start": rid_v2.make_time(time_start),
                    "time_end": rid_v2.make_time(time_end),
                },
                "uss_base_url": BASE_URL,
            },
        )
        if index < NetDSSMaxSubscriptionPerArea:
            assert resp.status_code == 200, resp.content
            resp_json = resp.json()
            assert "subscription" in resp_json
            assert "version" in resp_json["subscription"]
            versions.append(resp_json["subscription"]["version"])
        else:
            assert resp.status_code == 429, resp.content

    # clean up Subscription-limit Subscriptions
    for index in range(NetDSSMaxSubscriptionPerArea):
        resp = session_ridv2.delete(
            "{}/{}/{}".format(
                SUBSCRIPTION_PATH, ids(MULTI_SUB_TYPES[index]), versions[index]
            )
        )
        assert resp.status_code == 200


@default_scope(Scope.DisplayProvider)
def test_create_sub_with_too_long_end_time(ids, session_ridv2):
    """ASTM Compliance Test: DSS0060_MAX_SUBS_DURATION."""
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(
        hours=(NetDSSMaxSubscriptionDurationHours + 1)
    )

    resp = session_ridv2.put(
        "{}/{}".format(SUBSCRIPTION_PATH, ids(SUB_TYPE)),
        json={
            "extents": {
                "volume": {
                    "outline_polygon": {"vertices": common.VERTICES},
                    "altitude_lower": rid_v2.make_altitude(20),
                    "altitude_upper": rid_v2.make_altitude(400),
                },
                "time_start": rid_v2.make_time(time_start),
                "time_end": rid_v2.make_time(time_end),
            },
            "uss_base_url": BASE_URL,
        },
    )
    assert resp.status_code == 400, resp.content


@default_scope(Scope.DisplayProvider)
def test_update_sub_with_too_long_end_time(ids, session_ridv2):
    """ASTM Compliance Test: DSS0060_MAX_SUBS_DURATION."""
    time_start = datetime.datetime.utcnow()
    time_end = time_start + datetime.timedelta(seconds=10)

    resp = session_ridv2.put(
        "{}/{}".format(SUBSCRIPTION_PATH, ids(SUB_TYPE)),
        json={
            "extents": {
                "volume": {
                    "outline_polygon": {"vertices": common.VERTICES},
                    "altitude_lower": rid_v2.make_altitude(20),
                    "altitude_upper": rid_v2.make_altitude(400),
                },
                "time_start": rid_v2.make_time(time_start),
                "time_end": rid_v2.make_time(time_end),
            },
            "uss_base_url": BASE_URL,
        },
    )
    assert resp.status_code == 200, resp.content

    time_end = time_start + datetime.timedelta(
        hours=(NetDSSMaxSubscriptionDurationHours + 1)
    )
    resp = session_ridv2.put(
        "{}/{}".format(SUBSCRIPTION_PATH, ids(SUB_TYPE))
        + "/"
        + resp.json()["subscription"]["version"],
        json={
            "extents": {
                "volume": {
                    "outline_polygon": {"vertices": common.VERTICES},
                    "altitude_lower": rid_v2.make_altitude(20),
                    "altitude_upper": rid_v2.make_altitude(400),
                },
                "time_start": rid_v2.make_time(time_start),
                "time_end": rid_v2.make_time(time_end),
            },
            "uss_base_url": BASE_URL,
        },
    )
    assert resp.status_code == 400, resp.content


@default_scope(Scope.DisplayProvider)
def test_delete(ids, session_ridv2):
    resp = session_ridv2.get(
        "{}/{}".format(SUBSCRIPTION_PATH, ids(SUB_TYPE)), scope=Scope.DisplayProvider
    )
    if resp.status_code == 200:
        version = resp.json()["subscription"]["version"]
        resp = session_ridv2.delete(
            "{}/{}/{}".format(SUBSCRIPTION_PATH, ids(SUB_TYPE), version),
            scope=Scope.DisplayProvider,
        )
        assert resp.status_code == 200, resp.content
    elif resp.status_code == 404:
        # As expected.
        pass
