import os
import uuid
from datetime import timedelta
from typing import Tuple

import flask
from implicitdict import ImplicitDict
from loguru import logger

from monitoring.mock_uss.f3548v21.flight_planning import op_intent_from_flightinfo
from monitoring.mock_uss.flights.database import FlightRecord
from monitoring.mock_uss.scd_injection.routes_injection import (
    inject_flight,
    lock_flight,
    release_flight_lock,
    delete_flight,
    clear_area,
)
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    FlightInfo,
)
from monitoring.monitorlib.clients.mock_uss.mock_uss_scd_injection_api import (
    MockUSSUpsertFlightPlanRequest,
)
from monitoring.monitorlib.geotemporal import Volume4D
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
        req_body: MockUSSUpsertFlightPlanRequest = ImplicitDict.parse(
            json, MockUSSUpsertFlightPlanRequest
        )
    except ValueError as e:
        msg = "Create flight {} unable to parse JSON: {}".format(flight_plan_id, e)
        return msg, 400

    existing_flight = lock_flight(flight_plan_id, log)
    try:
        info = FlightInfo.from_flight_plan(req_body.flight_plan)
        op_intent = op_intent_from_flightinfo(info, str(uuid.uuid4()))
        new_flight = FlightRecord(
            flight_info=info,
            op_intent=op_intent,
            mod_op_sharing_behavior=req_body.behavior
            if "behavior" in req_body and req_body.behavior
            else None,
        )

        inject_resp = inject_flight(flight_plan_id, new_flight, existing_flight)
    finally:
        release_flight_lock(flight_plan_id, log)

    resp = api.UpsertFlightPlanResponse(
        planning_result=api.PlanningActivityResult(inject_resp.activity_result),
        flight_plan_status=api.FlightPlanStatus(inject_resp.flight_plan_status),
    )
    for k, v in inject_resp.items():
        if k not in {"planning_result", "flight_plan_status"}:
            resp[k] = v
    return flask.jsonify(resp), 200


@webapp.route("/flight_planning/v1/flight_plans/<flight_plan_id>", methods=["DELETE"])
@requires_scope(Scope.Plan)
def flight_planning_v1_delete_flight(flight_plan_id: str) -> Tuple[str, int]:
    """Implements flight deletion in SCD automated testing injection API."""
    del_resp = delete_flight(flight_plan_id)

    resp = api.DeleteFlightPlanResponse(
        planning_result=api.PlanningActivityResult(del_resp.activity_result),
        flight_plan_status=api.FlightPlanStatus(del_resp.flight_plan_status),
    )
    for k, v in del_resp.items():
        if k not in {"planning_result", "flight_plan_status"}:
            resp[k] = v
    return flask.jsonify(resp), 200


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

    clear_resp = clear_area(Volume4D.from_flight_planning_api(req.extent))

    resp = api.ClearAreaResponse(
        outcome=api.ClearAreaOutcome(
            success=clear_resp.success,
            message="See `details` field in response for more information",
            details=clear_resp,
        )
    )

    return flask.jsonify(resp), 200
