import functools
import os
import datetime
import copy
from loguru import logger


import flask
import yaml
from typing import Dict

from monitoring.monitorlib.fetch import QueryError, Query, describe_flask_query
from monitoring.monitorlib.mock_uss_interface.interuss_interaction import Interaction, Issue
from monitoring.mock_uss import webapp, require_config_value
from monitoring.mock_uss.interuss_logging.config import KEY_LOG_DIR

require_config_value(KEY_LOG_DIR)

def log_interaction(direction : str, method: str, type: str):
    '''
    Decorator for logging the REST calls between Mock USS to SUT
    Args:
        direction: incoming or outgoing
        method: GET or POST
        type: Op, Pos or Constr
    Returns:

    '''
    def inner_log(function):
        @functools.wraps(function)
        def wrapper_log(*args, **kwargs):
            interaction = None
            func_name = function.__name__
            try:
                result, query = function(*args, **kwargs)
                interaction = Interaction(query=query)
                return result, query
            except QueryError as q:
                issues = []
                issues.append(Issue(description=q.msg))
                interaction = Interaction(query=q.queries[0], reported_issues=issues)
                raise q
            finally:
                log_file(f"{direction}_{method}_{type}", interaction)

        return wrapper_log

    return inner_log

def log_file(code:str, content: Dict) -> str:
    log_path = webapp.config[KEY_LOG_DIR]
    n = len(os.listdir(log_path))
    basename = "{:06d}_{}_{}".format(
        n, code, datetime.datetime.now().strftime("%H%M%S_%f")
    )
    logname = "{}.yaml".format(basename)
    fullname = os.path.join(log_path, logname)

    dump = copy.deepcopy(content)
    dump["object_type"] = type(content).__name__
    mode = 'a' if os.path.exists(fullname) else 'w'
    with open(fullname, mode) as f:
        f.write(yaml.dump(dump, indent=2))


def log_flask_interaction(function):
    '''
    Decorator for logging flask request and response in an interaction
    Args:
        function

    Returns:
        function response
    '''
    @functools.wraps(function)
    def wrapper_log(*args, **kwargs):
        req = flask.request
        method = flask.request.method
        url = flask.request.url
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
        res = function(*args, **kwargs)
        rt = (datetime.datetime.utcnow() - st).total_seconds()
        logger.debug (f"res - {str(res)}")
        query = describe_flask_query(req, res, rt)
        issues = []
        if query.status_code != 200 or query.status_code != 204:
            issue = Issue(description=res.get_data(as_text=True))
            issues.append(issue)
        interaction = Interaction(query=query, reported_issues = issues)
        log_file(f"incoming_{method}_{type}", interaction)
        return res

    return wrapper_log
