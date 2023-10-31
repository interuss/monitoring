import os
from datetime import timedelta
from typing import Tuple

import flask
from implicitdict import ImplicitDict
from loguru import logger

from monitoring.mock_uss.scd_injection.routes_injection import (
    inject_flight,
    lock_flight,
    release_flight_lock,
    delete_flight,
    clear_area,
)
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    FlightInfo,
    AirspaceUsageState,
)
from monitoring.monitorlib.clients.mock_uss.mock_uss_scd_injection_api import (
    MockUSSInjectFlightRequest,
    MockUssFlightBehavior,
)
from uas_standards.interuss.automated_testing.flight_planning.v1 import api
from uas_standards.interuss.automated_testing.flight_planning.v1.constants import Scope
from uas_standards.interuss.automated_testing.scd.v1 import api as scd_api

from monitoring.mock_uss import webapp, require_config_value
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.config import KEY_BASE_URL
from monitoring.monitorlib.idempotency import idempotent_request


require_config_value(KEY_BASE_URL)

DEADLOCK_TIMEOUT = timedelta(seconds=5)


@webapp.route("/flight_planning/v1/status", methods=["GET"])
@requires_scope(Scope.DirectAutomatedTest)
def flight_planning_v1_status() -> Tuple[str, int]:
    json, code = injection_status()
    return flask.jsonify(json), code


def injection_status() -> Tuple[dict, int]:
    return (
        api.StatusResponse(
            status=api.StatusResponseStatus.Ready,
            api_name="Flight Planning Automated Testing Interface",
            api_version="v0.3.0",
        ),
        200,
    )


@webapp.route("/flight_planning/v1/flight_plans/<flight_plan_id>", methods=["PUT"])
@requires_scope(Scope.Plan)
@idempotent_request()
def flight_planning_v1_upsert_flight_plan(flight_plan_id: str) -> Tuple[str, int]:
    def log(msg: str) -> None:
        logger.debug(f"[upsert_plan/{os.getpid()}:{flight_plan_id}] {msg}")

    log("Starting handler")
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        req_body: api.UpsertFlightPlanRequest = ImplicitDict.parse(
            json, api.UpsertFlightPlanRequest
        )
    except ValueError as e:
        msg = "Create flight {} unable to parse JSON: {}".format(flight_plan_id, e)
        return msg, 400
    info = FlightInfo.from_flight_plan(req_body.flight_plan)
    req = MockUSSInjectFlightRequest(info.to_scd_inject_flight_request())
    if "behavior" in json:
        try:
            req.behavior = ImplicitDict.parse(json["behavior"], MockUssFlightBehavior)
        except ValueError as e:
            msg = f"Create flight {flight_plan_id} unable to parse `behavior` field: {str(e)}"
            return msg, 400

    existing_flight = lock_flight(flight_plan_id, log)
    try:
        if existing_flight:
            usage_state = existing_flight.flight_info.basic_information.usage_state
            if usage_state == AirspaceUsageState.Planned:
                old_status = api.FlightPlanStatus.Planned
            elif usage_state == AirspaceUsageState.InUse:
                old_status = api.FlightPlanStatus.OkToFly
            else:
                raise ValueError(f"Unrecognized usage_state '{usage_state}'")
        else:
            old_status = api.FlightPlanStatus.NotPlanned

        scd_resp, code = inject_flight(flight_plan_id, req, existing_flight)
    finally:
        release_flight_lock(flight_plan_id, log)

    if scd_resp.result == scd_api.InjectFlightResponseResult.Planned:
        result = api.PlanningActivityResult.Completed
        plan_status = api.FlightPlanStatus.Planned
        notes = None
    elif scd_resp.result == scd_api.InjectFlightResponseResult.ReadyToFly:
        result = api.PlanningActivityResult.Completed
        plan_status = api.FlightPlanStatus.OkToFly
        notes = None
    elif (
        scd_resp.result == scd_api.InjectFlightResponseResult.ConflictWithFlight
        or scd_resp.result == scd_api.InjectFlightResponseResult.Rejected
    ):
        result = api.PlanningActivityResult.Rejected
        plan_status = old_status
        notes = scd_resp.notes if "notes" in scd_resp else None
    elif scd_resp.result == scd_api.InjectFlightResponseResult.Failed:
        result = api.PlanningActivityResult.Failed
        plan_status = old_status
        notes = scd_resp.notes if "notes" in scd_resp else None
    else:
        raise ValueError(f"Unexpected scd inject_flight result '{scd_resp.result}'")

    resp = api.UpsertFlightPlanResponse(
        planning_result=result,
        notes=notes,
        flight_plan_status=plan_status,
    )
    for k, v in scd_resp.items():
        if k not in {"result", "notes", "operational_intent_id"}:
            resp[k] = v
    return flask.jsonify(resp), code


@webapp.route("/flight_planning/v1/flight_plans/<flight_plan_id>", methods=["DELETE"])
@requires_scope(Scope.Plan)
def flight_planning_v1_delete_flight(flight_plan_id: str) -> Tuple[str, int]:
    """Implements flight deletion in SCD automated testing injection API."""
    scd_resp, code = delete_flight(flight_plan_id)
    if code != 200:
        raise RuntimeError(
            f"DELETE flight plan endpoint expected code 200 from scd handler but received {code} instead"
        )

    if scd_resp.result == scd_api.DeleteFlightResponseResult.Closed:
        result = api.PlanningActivityResult.Completed
        status = api.FlightPlanStatus.Closed
    else:
        result = api.PlanningActivityResult.Failed
        status = (
            api.FlightPlanStatus.NotPlanned
        )  # delete_flight only fails like this when the flight doesn't exist
    kwargs = {"planning_result": result, "flight_plan_status": status}
    if "notes" in scd_resp:
        kwargs["notes"] = scd_resp.notes
    resp = api.DeleteFlightPlanResponse(**kwargs)

    return flask.jsonify(resp), code


@webapp.route("/flight_planning/v1/clear_area_requests", methods=["POST"])
@requires_scope(Scope.DirectAutomatedTest)
@idempotent_request()
def flight_planning_v1_clear_area() -> Tuple[str, int]:
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        req: api.ClearAreaRequest = ImplicitDict.parse(json, api.ClearAreaRequest)
    except ValueError as e:
        msg = "Unable to parse ClearAreaRequest JSON request: {}".format(e)
        return msg, 400

    scd_req = scd_api.ClearAreaRequest(
        request_id=req.request_id,
        extent=ImplicitDict.parse(req.extent, scd_api.Volume4D),
    )

    scd_resp, code = clear_area(scd_req)

    resp = ImplicitDict.parse(scd_resp, api.ClearAreaResponse)

    return flask.jsonify(resp), code
