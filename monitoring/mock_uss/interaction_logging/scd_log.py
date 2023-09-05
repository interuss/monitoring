from loguru import logger
from typing import List, Optional
from monitoring.monitorlib.clients import scd
from monitoring.mock_uss.interaction_logging.logger import (
    log_interaction,
    log_flask_interaction,
)

from monitoring.monitorlib.clients import QueryHook, query_hooks
from monitoring.monitorlib.clients.scd import (
    get_operational_intent_details,
    notify_operational_intent_details_changed,
)
from monitoring.monitorlib.fetch import Query
from monitoring.monitorlib.mock_uss_interface import ResponseHook, res_hooks
from flask import Request, Response
from monitoring.monitorlib.mock_uss_interface.interaction_log import Issue


logger.debug("Importing scd_log")


class LoggingHook(QueryHook):
    def on_query(
        self, query: Query, function, issues: Optional[List[Issue]] = None
    ) -> None:
        if function == get_operational_intent_details:
            log_interaction("outgoing", "GET", "Op", query, issues)
        elif function == notify_operational_intent_details_changed:
            log_interaction("outgoing", "POST", "Op", query, issues)


query_hooks.append(LoggingHook())


class ResponseLoggingHook(ResponseHook):
    def after_res(self, request: Request, response: Response):
        log_flask_interaction(request, response)


res_hooks.append(ResponseLoggingHook())
