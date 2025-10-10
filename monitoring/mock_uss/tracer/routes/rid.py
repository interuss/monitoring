import os

import arrow
import flask
from implicitdict import ImplicitDict, StringBasedDateTime
from loguru import logger
from termcolor import colored
from uas_standards.astm.f3411.v19.api import (
    PutIdentificationServiceAreaNotificationParameters as PutIdentificationServiceAreaNotificationParametersV19,
)
from uas_standards.astm.f3411.v22a.api import (
    PutIdentificationServiceAreaNotificationParameters as PutIdentificationServiceAreaNotificationParametersV22a,
)

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.tracer import context
from monitoring.mock_uss.tracer.log_types import RIDISANotification
from monitoring.mock_uss.tracer.template import _print_time_range
from monitoring.monitorlib import fetch
from monitoring.monitorlib.rid import RIDVersion

RESULT = ("", 204)


@webapp.route(
    "/tracer/f3411v19/<observation_area_id>/v1/uss/identification_service_areas/<isa_id>",
    methods=["POST"],
)
def tracer_rid_isa_notification_v19(
    observation_area_id: str, isa_id: str
) -> tuple[str, int]:
    return tracer_rid_isa_notification(isa_id, observation_area_id, RIDVersion.f3411_19)


@webapp.route(
    "/tracer/f3411v22a/<observation_area_id>/v2/uss/identification_service_areas/<isa_id>",
    methods=["POST"],
)
def tracer_rid_isa_notification_v22a(
    observation_area_id: str, isa_id: str
) -> tuple[str, int]:
    return tracer_rid_isa_notification(
        isa_id, observation_area_id, RIDVersion.f3411_22a
    )


def tracer_rid_isa_notification(
    isa_id: str, observation_area_id: str, rid_version: RIDVersion
) -> tuple[str, int]:
    """Implements RID ISA notification receiver."""
    logger.debug(f"Handling tracer_rid_isa_notification from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    log_name = context.tracer_logger.log_new(
        RIDISANotification(
            observation_area_id=observation_area_id,
            request=req,
            recorded_at=StringBasedDateTime(arrow.utcnow()),
        )
    )

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
                f"{label} {isa_id} v{version} ({owner}) updated {time_range} -> {log_name}"
            )
        else:
            logger.info(f"{label} {isa_id} ({owner}) deleted -> {log_name}")
    except ValueError as err:
        logger.error(
            f"{label} {isa_id} ({owner}) unable to decode JSON: {err} -> {log_name}"
        )

    return RESULT
