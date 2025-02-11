import os
from typing import Tuple

import arrow
import flask
from implicitdict import StringBasedDateTime
from loguru import logger
from termcolor import colored

from monitoring.mock_uss import webapp
from monitoring.mock_uss.tracer import context
from monitoring.mock_uss.tracer.log_types import BadRoute
from monitoring.monitorlib import fetch, versioning


@webapp.route("/tracer/status")
def tracer_status():
    logger.debug(f"Handling tracer_status from {os.getpid()}")
    return "Tracer ok {}".format(versioning.get_code_version())


from monitoring.mock_uss.tracer.routes import observation_areas, rid, scd, ui


@webapp.route("/tracer/<path:u_path>", methods=["GET", "PUT", "POST", "DELETE"])
def tracer_catch_all(u_path) -> Tuple[str, int]:
    logger.debug(f"Handling tracer_catch_all from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    log_name = context.tracer_logger.log_new(
        BadRoute(request=req, recorded_at=StringBasedDateTime(arrow.utcnow()))
    )

    claims = req.token
    owner = claims.get("sub", "<No owner in token>")
    label = colored("Bad route", "red")
    logger.error("{} to {} ({}): {}".format(label, u_path, owner, log_name))

    return f"Path is not a supported endpoint: {u_path}", 404
