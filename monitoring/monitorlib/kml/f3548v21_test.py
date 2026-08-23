from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21.api import (
    OperationalIntent,
    QueryOperationalIntentReferenceParameters,
    QueryOperationalIntentReferenceResponse,
)

from monitoring.monitorlib.kml.f3548v21 import full_op_intent, op_intent_refs_query


def _op_intent(**reference_overrides) -> OperationalIntent:
    reference = {
        "id": "",
        "manager": "",
        "uss_availability": "Unknown",
        "version": 0,
        "state": "Accepted",
        "time_start": {"value": "2024-01-01T00:00:00Z", "format": "RFC3339"},
        "time_end": {"value": "2024-01-01T01:00:00Z", "format": "RFC3339"},
        "uss_base_url": "",
        "subscription_id": "",
    }
    reference.update(reference_overrides)
    return ImplicitDict.parse(
        {"reference": reference, "details": {}},
        OperationalIntent,
    )


def test_full_op_intent_with_ovn():
    folder = full_op_intent(_op_intent(ovn="abc123"))
    assert folder.name.text == "'s P0 Accepted [0] @ abc123"


def test_full_op_intent_without_ovn():
    folder = full_op_intent(_op_intent())
    assert folder.name.text == "'s P0 Accepted [0] @ None"


def _expect_value_error(req: QueryOperationalIntentReferenceParameters) -> None:
    resp = ImplicitDict.parse(
        {"operational_intent_references": []}, QueryOperationalIntentReferenceResponse
    )
    try:
        op_intent_refs_query(req, resp)
    except ValueError as e:
        assert "req.area_of_interest is not defined" == str(e)
    else:
        raise AssertionError("Expected ValueError for missing area_of_interest")


def test_op_intent_refs_query_without_area_of_interest():
    _expect_value_error(
        ImplicitDict.parse({}, QueryOperationalIntentReferenceParameters)
    )


def test_op_intent_refs_query_with_falsy_area_of_interest():
    req = ImplicitDict.parse({}, QueryOperationalIntentReferenceParameters)
    req["area_of_interest"] = None
    _expect_value_error(req)
