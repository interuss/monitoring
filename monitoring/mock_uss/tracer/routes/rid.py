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
from ..template import _print_time_range

RESULT = ("", 204)


@webapp.route(
    "/tracer/f3411v19/<observation_area_id>/v1/uss/identification_service_areas/<isa_id>",
    methods=["POST"],
)
def tracer_rid_isa_notification_v19(
    observation_area_id: str, isa_id: str
) -> Tuple[str, int]:
    return tracer_rid_isa_notification(isa_id, RIDVersion.f3411_19)


@webapp.route(
    "/tracer/f3411v22a/<observation_area_id>/v2/uss/identification_service_areas/<isa_id>",
    methods=["POST"],
)
def tracer_rid_isa_notification_v22a(
    observation_area_id: str, isa_id: str
) -> Tuple[str, int]:
    return tracer_rid_isa_notification(isa_id, RIDVersion.f3411_22a)


def tracer_rid_isa_notification(id: str, rid_version: RIDVersion) -> Tuple[str, int]:
    """Implements RID ISA notification receiver."""
    logger.debug(f"Handling tracer_rid_isa_notification from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    req["endpoint"] = "identification_service_areas"
    log_name = context.tracer_logger.log_new("notify_isa", req)

    claims = req.token
    owner = claims.get("sub", "<No owner in token>")
    label = colored("ISA", "cyan")
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")

        # TODO: Use mutate.rid.ISAChangeNotification when fully implemented. See https://github.com/interuss/monitoring/pull/123/files/553f46b374623e3734634bb277548e06a2457cd6#r1255701016
        if rid_version == RIDVersion.f3411_19:
            notification = ImplicitDict.parse(
                json, PutIdentificationServiceAreaNotificationParametersV19
            )
        elif rid_version == RIDVersion.f3411_22a:
            notification = ImplicitDict.parse(
                json, PutIdentificationServiceAreaNotificationParametersV22a
            )
        else:
            raise NotImplementedError(f"RID version {rid_version} not yet supported")

        if notification.get("service_area", None):
            isa = notification.service_area
            owner_body = isa.owner
            if owner_body and owner_body != owner:
                owner = f"{owner} token|{owner_body} body"
            version = isa.version if isa.version else "<Unknown version>"
            if rid_version == RIDVersion.f3411_19:
                time_range = _print_time_range(isa.time_start, isa.time_end)
            elif rid_version == RIDVersion.f3411_22a:
                time_range = _print_time_range(isa.time_start.value, isa.time_end.value)
            else:
                raise NotImplementedError(
                    f"Unsupported RID Version {rid_version}. Unable to retrieve time range from isa response {isa}."
                )

            logger.info(
                f"{label} {id} v{version} ({owner}) updated {time_range} -> {log_name}"
            )
        else:
            logger.info(f"{label} {id} ({owner}) deleted -> {log_name}")
    except ValueError as err:
        logger.error(
            f"{label} {id} ({owner}) unable to decode JSON: {err} -> {log_name}"
        )

    return RESULT
