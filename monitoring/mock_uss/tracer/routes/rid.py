import os
from typing import Tuple

import flask
from loguru import logger
from termcolor import colored

from monitoring.mock_uss import webapp
from monitoring.monitorlib import fetch
from monitoring.monitorlib.rid import RIDVersion
from .. import context
from ..config import KEY_RID_VERSION
from ..template import _print_time_range

RESULT = ("", 204)
RID_VERSION = webapp.config[KEY_RID_VERSION]

def tracer_rid_isa_notification(id: str):
    req = fetch.describe_flask_request(flask.request)
    req["endpoint"] = "identification_service_areas"
    log_name = context.resources.logger.log_new("notify_isa", req)

    claims = req.token
    owner = claims.get("sub", "<No owner in token>")
    label = colored("ISA", "cyan")
    try:
        json = flask.request.json
        if json.get("service_area"):
            isa = json["service_area"]
            owner_body = isa.get("owner")
            if owner_body and owner_body != owner:
                owner = "{} token|{} body".format(owner, owner_body)
            version = isa.get("version", "<Unknown version>")
            time_range = _print_time_range(isa.get("time_start"), isa.get("time_end"))
            logger.info(
                "{} {} v{} ({}) updated{} -> {}".format(
                    label, id, version, owner, time_range, log_name
                )
            )
        else:
            logger.info("{} {} ({}) deleted -> {}".format(label, id, owner, log_name))
    except ValueError as e:
        logger.error(
            "{} {} ({}) unable to decode JSON: {} -> {}".format(
                label, id, owner, e, log_name
            )
        )

    return RESULT


if RID_VERSION == RIDVersion.f3411_19:
    @webapp.route(
        "/tracer/f3411v19/v1/uss/identification_service_areas/<id>", methods=["POST"]
    )
    def tracer_rid_v1_isa_notification(id: str) -> Tuple[str, int]:
        logger.debug(f"Handling tracer_rid_v1_isa_notification from {os.getpid()}")
        """Implements RID ISA notification receiver."""
        return tracer_rid_isa_notification(id)

elif RID_VERSION == RIDVersion.f3411_22a:
    @webapp.route(
        "/tracer/rid/f3411v22a/v2/uss/identification_service_areas/<id>", methods=["POST"]
    )
    def tracer_rid_v1_isa_notification(id: str) -> Tuple[str, int]:
        logger.debug(f"Handling tracer_rid_v2_isa_notification from {os.getpid()}")
        """Implements RID ISA notification receiver."""
        return tracer_rid_isa_notification(id)

else:
    logger.warning(f"Unsupported RID Version {RID_VERSION}. No routes mounted for RID notifications.")
