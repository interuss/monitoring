import datetime
import json
import os

import flask

from monitoring.mock_uss.app import require_config_value, webapp
from monitoring.mock_uss.interaction_logging.config import KEY_INTERACTIONS_LOG_DIR
from monitoring.monitorlib.clients import QueryHook, query_hooks
from monitoring.monitorlib.clients.mock_uss.interactions import (
    Interaction,
    QueryDirection,
)
from monitoring.monitorlib.fetch import Query, QueryType, describe_flask_query

require_config_value(KEY_INTERACTIONS_LOG_DIR)

# We use dashes between hours, minutes and seconds, because colons might be problematic for Windows,
# and the CI is unhappy about them in filenames.
LOGGED_INTERACTION_FILENAME_TIMESTAMP_FORMAT = "%Y-%m-%dT%H-%M-%S.%fZ"


def log_interaction(direction: QueryDirection, query: Query) -> None:
    """Logs the REST calls between Mock USS to SUT
    Args:
        direction: Whether this interaction was initiated or handled by this system.
        query: Full description of the interaction to log.
    """
    log_file(
        code=f"{direction.value}_{query.request.method}",
        content=Interaction(query=query, direction=direction),
    )


def log_file(code: str, content: Interaction) -> None:
    log_path = webapp.config[KEY_INTERACTIONS_LOG_DIR]
    n = len(os.listdir(log_path))
    basename = "{:06d}_{}_{}.json".format(
        n,
        code,
        content.interaction_time().strftime(
            LOGGED_INTERACTION_FILENAME_TIMESTAMP_FORMAT
        ),
    )
    with open(os.path.join(log_path, basename), "w") as f:
        json.dump(content, f)


class InteractionLoggingHook(QueryHook):
    def on_query(self, query: Query) -> None:
        # TODO: Make this configurable instead of hardcoding exactly these query types
        if "query_type" in query and query.query_type in {
            QueryType.F3548v21USSGetOperationalIntentDetails,
            QueryType.F3548v21USSNotifyOperationalIntentDetailsChanged,
            QueryType.F3411v19USSGetFlightDetails,
            QueryType.F3411v19USSPostIdentificationServiceArea,
            QueryType.F3411v19USSSearchFlights,
            QueryType.F3411v22aUSSSearchFlights,
            QueryType.F3411v22aUSSGetFlightDetails,
            QueryType.F3411v22aUSSPostIdentificationServiceArea,
        }:
            log_interaction(QueryDirection.Outgoing, query)


query_hooks.append(InteractionLoggingHook())


# https://stackoverflow.com/a/67856316
@webapp.before_request
def interaction_log_before_request():
    flask.Flask.custom_profiler = {"start": datetime.datetime.now(datetime.UTC)}


@webapp.after_request
def interaction_log_after_request(response):
    elapsed_s = (
        datetime.datetime.now(datetime.UTC) - flask.current_app.custom_profiler["start"]
    ).total_seconds()
    # TODO: Make this configurable instead of hardcoding exactly these query types
    if (
        "/uss/v1/" in flask.request.url
        or "/uss/identification_service_areas/" in flask.request.url
        or "/uss/flights" in flask.request.url
    ):
        query = describe_flask_query(flask.request, response, elapsed_s)
        log_interaction(QueryDirection.Incoming, query)
    return response
