import os
import uuid
from datetime import timedelta

import arrow
import flask
from implicitdict import ImplicitDict
from loguru import logger
from uas_standards.interuss.automated_testing.flight_planning.v1 import api
from uas_standards.interuss.automated_testing.flight_planning.v1.constants import Scope

from monitoring.mock_uss.app import require_config_value, webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.config import KEY_BASE_URL
from monitoring.mock_uss.f3548v21.flight_planning import op_intent_from_flightinfo
from monitoring.mock_uss.flights.database import FlightRecord, db
from monitoring.mock_uss.scd_injection.routes_injection import (
    clear_area,
    delete_flight,
    inject_flight,
    lock_flight,
    release_flight_lock,
)
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.clients.mock_uss.mock_uss_scd_injection_api import (
    MockUSSUpsertFlightPlanRequest,
)
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.idempotency import idempotent_request

require_config_value(KEY_BASE_URL)

DEADLOCK_TIMEOUT = timedelta(seconds=5)


@webapp.route("/flight_planning/v1/status", methods=["GET"])
@requires_scope(Scope.DirectAutomatedTest)
def flight_planning_v1_status() -> tuple[str, int]:
    json, code = injection_status()
    return flask.jsonify(json), code


def injection_status() -> tuple[dict, int]:
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
def flight_planning_v1_upsert_flight_plan(flight_plan_id: str) -> tuple[str, int]:
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
        msg = f"Create flight {flight_plan_id} unable to parse JSON: {e}"
        return msg, 400

    existing_flight = lock_flight(flight_plan_id, log)
    try:
        info = FlightInfo.from_flight_plan(req_body.flight_plan)
        op_intent = op_intent_from_flightinfo(info, str(uuid.uuid4()))
        new_flight = FlightRecord(
            flight_info=info,
            op_intent=op_intent,
            mod_op_sharing_behavior=(
                req_body.behavior
                if "behavior" in req_body and req_body.behavior
                else None
            ),
        )

        inject_resp = inject_flight(flight_plan_id, new_flight, existing_flight)

    finally:
        release_flight_lock(flight_plan_id, log)

    resp = api.UpsertFlightPlanResponse(
        planning_result=api.PlanningActivityResult(inject_resp.activity_result),
        flight_plan_status=api.FlightPlanStatus(inject_resp.flight_plan_status),
    )
    for k, v in inject_resp.items():
        if k not in {"planning_result", "flight_plan_status", "has_conflict"}:
            resp[k] = v
    return flask.jsonify(resp), 200


@webapp.route("/flight_planning/v1/flight_plans/<flight_plan_id>", methods=["DELETE"])
@requires_scope(Scope.Plan)
def flight_planning_v1_delete_flight(flight_plan_id: str) -> tuple[str, int]:
    """Implements flight deletion in SCD automated testing injection API."""
    del_resp, status_code = delete_flight(flight_plan_id)

    resp = api.DeleteFlightPlanResponse(
        planning_result=api.PlanningActivityResult(del_resp.activity_result),
        flight_plan_status=api.FlightPlanStatus(del_resp.flight_plan_status),
    )
    for k, v in del_resp.items():
        if k not in {"planning_result", "flight_plan_status"}:
            resp[k] = v
    return flask.jsonify(resp), status_code


@webapp.route("/flight_planning/v1/clear_area_requests", methods=["POST"])
@requires_scope(Scope.DirectAutomatedTest)
@idempotent_request()
def flight_planning_v1_clear_area() -> tuple[str, int]:
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        req: api.ClearAreaRequest = ImplicitDict.parse(json, api.ClearAreaRequest)
    except ValueError as e:
        msg = f"Unable to parse ClearAreaRequest JSON request: {e}"
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


@webapp.route("/flight_planning/v1/user_notifications", methods=["GET"])
@requires_scope(Scope.Plan)
def flight_planning_v1_user_notifications() -> tuple[str, int]:
    if "after" not in flask.request.args:
        return (
            'Missing required "after" parameter',
            400,
        )
    try:
        after = arrow.get(flask.request.args["after"])
    except ValueError as e:
        return (
            f"Error parsing after: {e}",
            400,
        )

    if "before" not in flask.request.args:
        before = arrow.utcnow()
    else:
        try:
            before = arrow.get(flask.request.args["before"])
        except ValueError as e:
            return (
                f"Error parsing before: {e}",
                400,
            )

    if before < after:
        return (
            f"'Before' ({before}) is after 'after' ({after})",
            400,
        )

    final_list: list[api.UserNotification] = []

    for user_notification in db.value.flight_planning_notifications:
        if after.datetime <= user_notification.observed_at.datetime <= before.datetime:
            final_list.append(
                api.UserNotification(
                    observed_at=api.Time(value=user_notification.observed_at),
                    conflicts=user_notification.conflicts.to_api(),
                )
            )

    r = api.QueryUserNotificationsResponse(user_notifications=final_list)

    return flask.jsonify(r), 200
