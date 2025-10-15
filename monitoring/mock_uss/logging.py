from __future__ import annotations

import json
import os

import flask
import loguru
from flask import Request, Response
from loguru import logger

from monitoring.mock_uss.app import webapp


def _get_request_id(req: Request) -> str:
    try:
        return f"[{os.getpid()}] {req.date} {req.method} {req.url}"
    except RuntimeError:  # In some edge case, we may be outside a request context
        return ""


class RequestLogger:
    _request_id: str
    _loguru_hook: int | None = None
    _report_log: bool = True
    messages: list[str]

    def __init__(self):
        self.messages = []

    def add_to_loguru(self) -> None:
        self._request_id = _get_request_id(flask.request)
        self._loguru_hook = logger.add(
            self.log,
            format="[{time:YYYY-MM-DD HH:mm:ss.SSS} {level: <8} {name}:{function}:{line}] {message}",
        )

    def log(self, msg: loguru.Message) -> None:
        if (
            self._report_log
            and _get_request_id(flask.request) == self._request_id
            and self._request_id
        ):
            self.messages.append(msg)

    def do_not_report(self) -> None:
        self._report_log = False

    def get_response(self, resp: Response) -> Response:
        if self._report_log and resp.is_json and self.messages:
            body = resp.json
            if body is not None and "log_messages" not in body:
                body["log_messages"] = self.messages
            resp.data = json.dumps(body)
        return resp

    def remove_from_loguru(self) -> None:
        if self._loguru_hook is not None:
            logger.remove(self._loguru_hook)
            self._loguru_hook = None


_REQUEST_LOGGER_FIELD = "request_logger"


def get_request_logger() -> RequestLogger | None:
    if hasattr(flask.request, _REQUEST_LOGGER_FIELD):
        return getattr(flask.request, _REQUEST_LOGGER_FIELD)
    else:
        return None


def disable_log_reporting_for_request():
    request_logger = get_request_logger()
    if request_logger is not None:
        request_logger.do_not_report()


@webapp.before_request
def begin_request_log() -> None:
    request_logger = RequestLogger()
    request_logger.add_to_loguru()
    setattr(flask.request, _REQUEST_LOGGER_FIELD, request_logger)


@webapp.after_request
def add_request_log(resp: Response):
    request_logger = get_request_logger()
    if request_logger is not None:
        return request_logger.get_response(resp)
    else:
        return resp


@webapp.teardown_request
def end_request_log(e: BaseException | None) -> None:
    request_logger = get_request_logger()
    if request_logger is not None:
        request_logger.remove_from_loguru()
