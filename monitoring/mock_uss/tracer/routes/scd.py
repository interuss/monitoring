import os
from typing import Tuple

import flask
from loguru import logger
from termcolor import colored

from monitoring.mock_uss import webapp
from monitoring.monitorlib import fetch, infrastructure
from . import context
from ..template import _print_time_range

RESULT = ("", 204)


@webapp.route(
    "/tracer/f3548v21/<observation_area_id>/uss/v1/operational_intents",
    methods=["POST"],
)
def tracer_scd_v21_operation_notification(observation_area_id: str) -> Tuple[str, int]:
    """Implements SCD Operation notification receiver."""
    logger.debug(f"Handling tracer_scd_v21_operation_notification from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    req["endpoint"] = "operational_intents"
    log_name = context.tracer_logger.log_new("notify_op", req)

    claims = req.token
    owner = claims.get("sub", "<No owner in token>")
    label = colored("Operation", "blue")
    try:
        json = flask.request.json
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
                    owner = "{} token|{} body".format(owner, owner_body)
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
                "{} {} {} {} v{} ({}) OVN[{}] updated{} -> {}".format(
                    label,
                    state,
                    priority_text,
                    id,
                    version,
                    owner,
                    ovn,
                    time_range,
                    log_name,
                )
            )
        else:
            logger.info("{} {} ({}) deleted -> {}".format(label, id, owner, log_name))
    except ValueError as e:
        logger.error(
            "{} ({}) unable to decode JSON: {} -> {}".format(label, owner, e, log_name)
        )

    return RESULT


@webapp.route(
    "/tracer/f3548v21/<observation_area_id>/uss/v1/constraints", methods=["POST"]
)
def tracer_scd_v21_constraint_notification(observation_area_id: str) -> Tuple[str, int]:
    """Implements SCD Constraint notification receiver."""
    logger.debug(f"Handling tracer_scd_v21_constraint_notification from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    req["endpoint"] = "constraints"
    log_name = context.tracer_logger.log_new("notify_constraint", req)

    claims = infrastructure.get_token_claims({k: v for k, v in flask.request.headers})
    owner = claims.get("sub", "<No owner in token>")
    label = colored("Constraint", "magenta")
    try:
        json = flask.request.json
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
                    owner = "{} token|{} body".format(owner, owner_body)
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
                "{} {} {} v{} ({}) OVN[{}] updated{} -> {}".format(
                    label, type, id, version, owner, ovn, time_range, log_name
                )
            )
        else:
            logger.info("{} {} ({}) deleted -> {}".format(label, id, owner, log_name))
    except ValueError as e:
        logger.error(
            "{} ({}) unable to decode JSON: {} -> {}".format(label, owner, e, log_name)
        )

    return RESULT
