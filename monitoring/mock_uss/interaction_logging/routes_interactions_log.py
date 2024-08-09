import datetime
import json
import os
from typing import Tuple, List

from flask import request, jsonify, Response
from implicitdict import ImplicitDict, StringBasedDateTime
from loguru import logger

from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.interaction_logging.config import KEY_INTERACTIONS_LOG_DIR
from monitoring.monitorlib.clients.mock_uss.interactions import (
    Interaction,
    ListLogsResponse,
)
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    SCOPE_SCD_QUALIFIER_INJECT,
)

CLIENT_CLOCK_SKEW_BUFFER = datetime.timedelta(seconds=5)


@webapp.route("/mock_uss/interuss_logging/logs", methods=["GET"])
@requires_scope(SCOPE_SCD_QUALIFIER_INJECT)
def interaction_logs() -> Tuple[Response, int]:
    """
    Returns all the interaction logs with requests that were
    received or initiated between 'from_time' and now
    Eg - http:/.../mock_uss/interuss_logging/logs?from_time=2023-08-30T20:48:21.900000Z
    """
    from_time_param = request.args.get("from_time", "1900-01-01T00:00:00Z")
    from_time = StringBasedDateTime(from_time_param)
    log_path = webapp.config[KEY_INTERACTIONS_LOG_DIR]

    if not os.path.exists(log_path):
        raise ValueError(f"Configured log path {log_path} does not exist")

    # individual interactions are logged to a file of the form <index>_<direction>_<method>_<timestamp>.json, eg
    # 000001_Incoming_GET_2023-08-30T20:48:21.900000Z.json
    interactions: List[Interaction] = []
    for fname in os.listdir(log_path):
        # Parse the interaction time from the file name:
        fname_parts = fname.split("_")
        if len(fname_parts) != 4:
            # We may just want to fail hard here to let users know something is likely very wrong
            logger.warning(
                f"Skipping file {fname} as it does not match the expected format"
            )
            continue
        interaction_time_str = fname_parts[3].split(".")[0]
        interaction_time = StringBasedDateTime(interaction_time_str)
        # Add a buffer to look slightly before the from_time to account for possible clock skew and the fact
        # that the timestamp used in the filename is based on the mock_uss clock, not the event time
        # from the perspective of the client.
        if interaction_time.datetime < (from_time.datetime - CLIENT_CLOCK_SKEW_BUFFER):
            continue
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
