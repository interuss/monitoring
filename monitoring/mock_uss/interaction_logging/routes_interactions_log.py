from typing import Tuple, List
import yaml
import os
from implicitdict import ImplicitDict, StringBasedDateTime
from flask import request, abort, jsonify
from yaml.constructor import ConstructorError
from loguru import logger

from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    SCOPE_SCD_QUALIFIER_INJECT,
)
from monitoring.monitorlib.mock_uss_interface.interaction_log import (
    Interaction,
    Issue,
    ListLogsResponse,
)

from monitoring.mock_uss.interaction_logging.config import KEY_INTERACTIONS_LOG_DIR


@webapp.route("/mock_uss/interuss/log", methods=["GET"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
def interaction_logs() -> Tuple[str, int]:
    """
    Returns all the interaction logs with requests that were
    received or initiated between 'from_time' and now
    Eg - http:/.../mock_uss/interuss/log?from_time=2023-08-30T20:48:21.900000Z
    """
    from_time_param = request.args.get("from_time")
    from_time = StringBasedDateTime(from_time_param)
    log_path = webapp.config[KEY_INTERACTIONS_LOG_DIR]
    n = len(os.listdir(log_path))

    if not os.path.exists(log_path):
        abort(404)
    interactions: List[Interaction] = []
    for fname in os.listdir(log_path):
        with open(os.path.join(log_path, fname), "r") as f:
            obj = {}
            try:
                for obj in yaml.full_load_all(f):
                    interaction = ImplicitDict.parse(obj, Interaction)
                    if (
                        ("received_at" in interaction.query.request)
                        and interaction.query.request.received_at.datetime
                        > from_time.datetime
                    ):
                        interactions.append(interaction)
                    elif (
                        "initiated_at" in interaction.query.request
                        and interaction.query.request.initiated_at.datetime
                        > from_time.datetime
                    ):
                        interactions.append(interaction)
                    else:
                        logger.error(
                            f"There is no received_at or initiated_at request after {from_time_param} the request in {fname}"
                        )
            except (ConstructorError, KeyError) as e:
                logger.error(f"Error occured in reading interaction - {e}")
                logger.debug(f"Contents of {fname} - {obj}")

    return jsonify(ListLogsResponse(interactions=interactions)), 200


@webapp.route("/mock_uss/interuss/logs", methods=["DELETE"])
@requires_scope([SCOPE_SCD_QUALIFIER_INJECT])
def delete_interaction_logs() -> Tuple[str, int]:
    """Deletes all the files under the logging directory"""
    log_path = webapp.config[KEY_INTERACTIONS_LOG_DIR]

    if not os.path.exists(log_path):
        abort(404)
    logger.debug(f"Files in {log_path} - {os.listdir(log_path)}")
    n = len(os.listdir(log_path))

    for file in os.listdir(log_path):
        file_path = os.path.join(log_path, file)
        os.remove(file_path)
        logger.debug(f"Removed log file - {file_path}")

    return f"Removed {n} files", 200
