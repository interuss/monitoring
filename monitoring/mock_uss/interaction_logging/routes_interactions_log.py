from typing import Tuple, List
import json
import os
from implicitdict import ImplicitDict, StringBasedDateTime
from flask import request, jsonify
from loguru import logger

from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    SCOPE_SCD_QUALIFIER_INJECT,
)
from monitoring.monitorlib.clients.mock_uss.interactions import (
    Interaction,
    ListLogsResponse,
)

from monitoring.mock_uss.interaction_logging.config import KEY_INTERACTIONS_LOG_DIR


@webapp.route("/mock_uss/interuss_logging/logs", methods=["GET"])
@requires_scope(SCOPE_SCD_QUALIFIER_INJECT)
def interaction_logs() -> Tuple[str, int]:
    """
    Returns all the interaction logs with requests that were
    received or initiated between 'from_time' and now
    Eg - http:/.../mock_uss/interuss/log?from_time=2023-08-30T20:48:21.900000Z
    """
    from_time_param = request.args.get("from_time", "1900-01-01T00:00:00Z")
    from_time = StringBasedDateTime(from_time_param)
    log_path = webapp.config[KEY_INTERACTIONS_LOG_DIR]

    if not os.path.exists(log_path):
        raise ValueError(f"Configured log path {log_path} does not exist")

    interactions: List[Interaction] = []
    for fname in os.listdir(log_path):
        with open(os.path.join(log_path, fname), "r") as f:
            try:
                obj = json.load(f)
                interaction = ImplicitDict.parse(obj, Interaction)
                if "received_at" in interaction.query.request:
                    if (
                        interaction.query.request.received_at.datetime
                        >= from_time.datetime
                    ):
                        interactions.append(interaction)
                elif "initiated_at" in interaction.query.request:
                    if (
                        interaction.query.request.initiated_at.datetime
                        >= from_time.datetime
                    ):
                        interactions.append(interaction)
                else:
                    raise ValueError(
                        f"There is no received_at or initiated_at field in the request in {fname}"
                    )

            except (KeyError, ValueError) as e:
                msg = f"Error occurred in reading interaction from file {fname}: {e}"
                raise type(e)(msg)

    return jsonify(ListLogsResponse(interactions=interactions)), 200


@webapp.route("/mock_uss/interuss_logging/logs", methods=["DELETE"])
@requires_scope(SCOPE_SCD_QUALIFIER_INJECT)
def delete_interaction_logs() -> Tuple[str, int]:
    """Deletes all the files under the logging directory"""
    log_path = webapp.config[KEY_INTERACTIONS_LOG_DIR]

    if not os.path.exists(log_path):
        raise ValueError(f"Configured log path {log_path} does not exist")

    logger.debug(f"Number of files in {log_path}: {len(os.listdir(log_path))}")

    num_removed = 0
    for file in os.listdir(log_path):
        file_path = os.path.join(log_path, file)
        os.remove(file_path)
        logger.debug(f"Removed log file - {file_path}")
        num_removed = num_removed + 1

    return f"Removed {num_removed} files", 200
