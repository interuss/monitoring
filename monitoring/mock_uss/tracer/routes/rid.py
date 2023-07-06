import os
from typing import Tuple

import flask
from loguru import logger
from termcolor import colored

from implicitdict import ImplicitDict
from monitoring.mock_uss import webapp
from monitoring.monitorlib import fetch
from monitoring.monitorlib.rid import RIDVersion
from uas_standards.astm.f3411.v19.api import (
    PutIdentificationServiceAreaNotificationParameters as PutIdentificationServiceAreaNotificationParametersV19,
)
from uas_standards.astm.f3411.v22a.api import (
    PutIdentificationServiceAreaNotificationParameters as PutIdentificationServiceAreaNotificationParametersV22a,
)
from .. import context
from ..config import KEY_RID_VERSION
from ..template import _print_time_range

RESULT = ("", 204)
RID_VERSION = webapp.config[KEY_RID_VERSION]


if RID_VERSION == RIDVersion.f3411_19:
    path = "/tracer/f3411v19/v1/uss/identification_service_areas/<id>"
elif RID_VERSION == RIDVersion.f3411_22a:
    path = "/tracer/f3411v22a/v2/uss/identification_service_areas/<id>"
else:
    raise NotImplementedError(
        f"Unsupported RID Version {RID_VERSION}. No routes mounted for RID notifications."
    )


@webapp.route(path, methods=["POST"])
def tracer_rid_isa_notification(id: str) -> Tuple[str, int]:
    """Implements RID ISA notification receiver."""
    logger.debug(f"Handling tracer_rid_isa_notification from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    req["endpoint"] = "identification_service_areas"
    log_name = context.resources.logger.log_new("notify_isa", req)

    claims = req.token
    owner = claims.get("sub", "<No owner in token>")
    label = colored("ISA", "cyan")
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        if RID_VERSION == RIDVersion.f3411_19:
            notification = ImplicitDict.parse(
                json, PutIdentificationServiceAreaNotificationParametersV19
            )
        if RID_VERSION == RIDVersion.f3411_22a:
            notification = ImplicitDict.parse(
                json, PutIdentificationServiceAreaNotificationParametersV22a
            )

        if notification.get("service_area", None):
            isa = notification.service_area
            owner_body = isa.owner
            if owner_body and owner_body != owner:
                owner = f"{owner} token|{owner_body} body"
            version = isa.version if isa.version else "<Unknown version>"
            if RID_VERSION == RIDVersion.f3411_19:
                time_range = _print_time_range(isa.time_start, isa.time_end)
            elif RID_VERSION == RIDVersion.f3411_22a:
                time_range = _print_time_range(isa.time_start.value, isa.time_end.value)
            else:
                raise NotImplementedError(
                    f"Unsupported RID Version {RID_VERSION}. Unable to retrieve time range from isa response {isa}."
                )

            logger.info(
                f"{label} {id} v{version} ({owner}) updated{time_range} -> {log_name}"
            )
        else:
            logger.info(f"{label} {id} ({owner}) deleted -> {log_name}")
    except ValueError as err:
        logger.error(
            f"{label} {id} ({owner}) unable to decode JSON: {err} -> {log_name}"
        )

    return RESULT
