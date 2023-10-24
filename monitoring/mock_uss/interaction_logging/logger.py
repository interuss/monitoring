import os
import datetime

import flask
import json

from monitoring.mock_uss import webapp, require_config_value
from monitoring.mock_uss.interaction_logging.config import KEY_INTERACTIONS_LOG_DIR
from monitoring.monitorlib.clients.mock_uss.interactions import (
    Interaction,
    QueryDirection,
)
from monitoring.monitorlib.clients import QueryHook, query_hooks
from monitoring.monitorlib.fetch import Query, describe_flask_query, QueryType

require_config_value(KEY_INTERACTIONS_LOG_DIR)


def log_interaction(direction: QueryDirection, query: Query) -> None:
    """Logs the REST calls between Mock USS to SUT
    Args:
        direction: Whether this interaction was initiated or handled by this system.
        query: Full description of the interaction to log.
    """
    interaction: Interaction = Interaction(query=query, direction=direction)
    method = query.request.method
    log_file(f"{direction}_{method}", interaction)


def log_file(code: str, content: Interaction) -> None:
    log_path = webapp.config[KEY_INTERACTIONS_LOG_DIR]
    n = len(os.listdir(log_path))
    basename = "{:06d}_{}_{}".format(
        n, code, datetime.datetime.now().strftime("%H%M%S_%f")
    )
    logname = "{}.json".format(basename)
    fullname = os.path.join(log_path, logname)

    with open(fullname, "w") as f:
        json.dump(content, f)


class InteractionLoggingHook(QueryHook):
    def on_query(self, query: Query) -> None:
        # TODO: Make this configurable instead of hardcoding exactly these query types
        if "query_type" in query and query.query_type in {
            QueryType.F3548v21USSGetOperationalIntentDetails,
            QueryType.F3548v21USSNotifyOperationalIntentDetailsChanged,
        }:
            log_interaction(QueryDirection.Outgoing, query)


query_hooks.append(InteractionLoggingHook())


# https://stackoverflow.com/a/67856316
@webapp.before_request
def interaction_log_before_request():
    flask.Flask.custom_profiler = {"start": datetime.datetime.utcnow()}


@webapp.after_request
def interaction_log_after_request(response):
    elapsed_s = (
        datetime.datetime.utcnow() - flask.current_app.custom_profiler["start"]
    ).total_seconds()
    # TODO: Make this configurable instead of hardcoding exactly these query types
    if "/uss/v1/" in flask.request.url:
        query = describe_flask_query(flask.request, response, elapsed_s)
        log_interaction(QueryDirection.Incoming, query)
    return response
