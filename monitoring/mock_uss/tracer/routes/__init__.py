import os

import arrow
import flask
from implicitdict import StringBasedDateTime
from loguru import logger
from termcolor import colored

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.tracer import context
from monitoring.mock_uss.tracer.log_types import BadRoute
from monitoring.mock_uss.tracer.routes import observation_areas as observation_areas
from monitoring.mock_uss.tracer.routes import rid as rid
from monitoring.mock_uss.tracer.routes import scd as scd
from monitoring.mock_uss.tracer.routes import ui as ui
from monitoring.monitorlib import fetch, versioning


@webapp.route("/tracer/status")
def tracer_status():
    logger.debug(f"Handling tracer_status from {os.getpid()}")
    return f"Tracer ok {versioning.get_code_version()}"


@webapp.route("/tracer/<path:u_path>", methods=["GET", "PUT", "POST", "DELETE"])
def tracer_catch_all(u_path) -> tuple[str, int]:
    logger.debug(f"Handling tracer_catch_all from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    log_name = context.tracer_logger.log_new(
        BadRoute(request=req, recorded_at=StringBasedDateTime(arrow.utcnow()))
    )

    claims = req.token
    owner = claims.get("sub", "<No owner in token>")
    label = colored("Bad route", "red")
    logger.error(f"{label} to {u_path} ({owner}): {log_name}")

    return f"Path is not a supported endpoint: {u_path}", 404
