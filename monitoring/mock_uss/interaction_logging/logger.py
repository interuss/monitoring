import functools
import os
import datetime
import copy
from loguru import logger
from typing import List, Optional

import flask
import yaml
from typing import Dict

from monitoring.monitorlib.fetch import QueryError, Query, describe_flask_query
from monitoring.monitorlib.mock_uss_interface.interaction_log import (
    Interaction,
    Issue,
)
from monitoring.mock_uss import webapp, require_config_value
from monitoring.mock_uss.interaction_logging.config import KEY_INTERACTIONS_LOG_DIR
from flask import Request, Response

require_config_value(KEY_INTERACTIONS_LOG_DIR)


def log_interaction(
    direction: str, method: str, type: str, query: Query, issues: Optional[List[Issue]]
):
    """
    Logs the REST calls between Mock USS to SUT
    Args:
        direction: incoming or outgoing
        method: GET or POST
        type: Op, Pos or Constr
    Returns:

    """
    interaction: Interaction = Interaction(query=query, reported_issues=issues)
    log_file(f"{direction}_{method}_{type}", interaction)


def log_file(code: str, content: Interaction) -> str:
    log_path = webapp.config[KEY_INTERACTIONS_LOG_DIR]
    n = len(os.listdir(log_path))
    basename = "{:06d}_{}_{}".format(
        n, code, datetime.datetime.now().strftime("%H%M%S_%f")
    )
    logname = "{}.yaml".format(basename)
    fullname = os.path.join(log_path, logname)

    dump = copy.deepcopy(content)
    dump["object_type"] = type(content).__name__
    mode = "a" if os.path.exists(fullname) else "w"
    with open(fullname, mode) as f:
        f.write(yaml.dump(dump, indent=2))


def log_flask_interaction(request: Request, response: Response):
    """
    Logs flask request and response in an interaction
    Args:
        function

    Returns:
        function response
    """
    req = flask.request
    method = req.method
    url = req.url
    if "/uss/v1/" not in url:
        return
    type = ""
    if "telemetry" in url:
        type = "Pos"
    elif "operational_intent" in url:
        type = "Op"
    elif "constraint" in url:
        type = "Constr"
    else:
        type = "Unknown"
    st = datetime.datetime.utcnow()
    rt = (datetime.datetime.utcnow() - st).total_seconds()
    logger.debug(f"res - {str(response)}")
    query = describe_flask_query(req, response, rt)
    issues = []
    if query.status_code != 200 or query.status_code != 204:
        issue = Issue(description=response.get_data(as_text=True))
        issues.append(issue)
    interaction = Interaction(query=query, reported_issues=issues)
    log_file(f"incoming_{method}_{type}", interaction)
    return response
