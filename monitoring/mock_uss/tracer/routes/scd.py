import os

import arrow
import flask
from implicitdict import StringBasedDateTime
from loguru import logger
from termcolor import colored

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.tracer import context
from monitoring.mock_uss.tracer.log_types import (
    ConstraintNotification,
    OperationalIntentNotification,
)
from monitoring.mock_uss.tracer.template import _print_time_range
from monitoring.monitorlib import fetch, infrastructure

RESULT = ("", 204)


@webapp.route(
    "/tracer/f3548v21/<observation_area_id>/uss/v1/operational_intents",
    methods=["POST"],
)
def tracer_scd_v21_operation_notification(observation_area_id: str) -> tuple[str, int]:
    """Implements SCD Operation notification receiver."""
    logger.debug(f"Handling tracer_scd_v21_operation_notification from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    log_name = context.tracer_logger.log_new(
        OperationalIntentNotification(
            observation_area_id=observation_area_id,
            request=req,
            recorded_at=StringBasedDateTime(arrow.utcnow()),
        )
    )

    claims = req.token
    owner = claims.get("sub", "<No owner in token>")
    label = colored("Operation", "blue")
    try:
        json = flask.request.json

        if json is None:
            raise ValueError("No json in request")

        id = json.get("operational_intent_id", "<Unknown ID>")
        if json.get("operational_intent"):
            op = json["operational_intent"]
            version = "<Unknown version>"
            ovn = "<Unknown OVN>"
            time_range = ""
            if op.get("reference"):
                op_ref = op["reference"]
                owner_body = op_ref.get("owner")
                if owner_body and owner_body != owner:
                    owner = f"{owner} token|{owner_body} body"
                version = op_ref.get("version", version)
                ovn = op_ref.get("ovn", ovn)
                time_range = _print_time_range(
                    op_ref.get("time_start", {}).get("value"),
                    op_ref.get("time_end", {}).get("value"),
                )
            state = "<Unknown state>"
            priority = 0
            if op.get("details"):
                op_details = op["details"]
                state = op_details.get("state")
                priority = op_details.get("priority", 0)
            priority_text = str(priority)
            logger.info(
                f"{label} {state} {priority_text} {id} v{version} ({owner}) OVN[{ovn}] updated{time_range} -> {log_name}"
            )
        else:
            logger.info(f"{label} {id} ({owner}) deleted -> {log_name}")
    except ValueError as e:
        logger.error(f"{label} ({owner}) unable to decode JSON: {e} -> {log_name}")

    return RESULT


@webapp.route(
    "/tracer/f3548v21/<observation_area_id>/uss/v1/constraints", methods=["POST"]
)
def tracer_scd_v21_constraint_notification(observation_area_id: str) -> tuple[str, int]:
    """Implements SCD Constraint notification receiver."""
    logger.debug(f"Handling tracer_scd_v21_constraint_notification from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    log_name = context.tracer_logger.log_new(
        ConstraintNotification(
            observation_area_id=observation_area_id,
            request=req,
            recorded_at=StringBasedDateTime(arrow.utcnow()),
        )
    )

    claims = infrastructure.get_token_claims({k: v for k, v in flask.request.headers})
    owner = claims.get("sub", "<No owner in token>")
    label = colored("Constraint", "magenta")
    try:
        json = flask.request.json

        if json is None:
            raise ValueError("No json in request")

        id = json.get("constraint_id", "<Unknown ID>")
        if json.get("constraint"):
            constraint = json["constraint"]
            version = "<Unknown version>"
            ovn = "<Unknown OVN>"
            time_range = ""
            if constraint.get("reference"):
                constraint_ref = constraint["reference"]
                owner_body = constraint_ref.get("owner")
                if owner_body and owner_body != owner:
                    owner = f"{owner} token|{owner_body} body"
                version = constraint_ref.get("version", version)
                ovn = constraint_ref.get("ovn", ovn)
                time_range = _print_time_range(
                    constraint_ref.get("time_start", {}).get("value"),
                    constraint_ref.get("time_end", {}).get("value"),
                )
            type = "<Unspecified type>"
            if constraint.get("details"):
                constraint_details = constraint["details"]
                type = constraint_details.get("type")
            logger.info(
                f"{label} {type} {id} v{version} ({owner}) OVN[{ovn}] updated{time_range} -> {log_name}"
            )
        else:
            logger.info(f"{label} {id} ({owner}) deleted -> {log_name}")
    except ValueError as e:
        logger.error(f"{label} ({owner}) unable to decode JSON: {e} -> {log_name}")

    return RESULT
