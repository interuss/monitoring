import datetime
import json
import os
import traceback
from typing import Dict, Optional, List

import flask
from loguru import logger
import requests
import urllib3
import yaml
from yaml.representer import Representer

from implicitdict import ImplicitDict, StringBasedDateTime
from monitoring.monitorlib import infrastructure


TIMEOUTS = (5, 5)  # Timeouts of `connect` and `read` in seconds
ATTEMPTS = (
    5  # Number of attempts to query when experiencing a retryable error like a timeout
)


class RequestDescription(ImplicitDict):
    method: str
    url: str
    headers: Optional[dict]
    json: Optional[dict] = None
    body: Optional[str] = None

    initiated_at: Optional[StringBasedDateTime]
    received_at: Optional[StringBasedDateTime]

    def __init__(self, *args, **kwargs):
        super(RequestDescription, self).__init__(*args, **kwargs)
        if "headers" not in self:
            self.headers = {}

    @property
    def token(self) -> Dict:
        return infrastructure.get_token_claims(self.headers)

    @property
    def timestamp(self) -> datetime.datetime:
        if "initiated_at" in self:
            # This was an outgoing request
            return self.initiated_at.datetime
        elif "received_at" in self:
            # This was an incoming request
            return self.received_at.datetime
        else:
            raise KeyError(
                "RequestDescription missing both initiated_at and received_at"
            )


yaml.add_representer(RequestDescription, Representer.represent_dict)


def describe_flask_request(request: flask.Request) -> RequestDescription:
    headers = {k: v for k, v in request.headers}
    kwargs = {
        "method": request.method,
        "url": request.url,
        "received_at": StringBasedDateTime(datetime.datetime.utcnow()),
        "headers": headers,
    }
    try:
        kwargs["json"] = request.json
    except ValueError:
        kwargs["body"] = request.data.decode("utf-8")
    return RequestDescription(**kwargs)


def describe_request(
    req: requests.PreparedRequest, initiated_at: datetime.datetime
) -> RequestDescription:
    headers = {k: v for k, v in req.headers.items()}
    kwargs = {
        "method": req.method,
        "url": req.url,
        "initiated_at": StringBasedDateTime(initiated_at),
        "headers": headers,
    }
    body = req.body.decode("utf-8") if req.body else None
    try:
        if body:
            kwargs["json"] = json.loads(body)
        else:
            kwargs["body"] = body
    except ValueError:
        kwargs["body"] = body
    return RequestDescription(**kwargs)


class ResponseDescription(ImplicitDict):
    code: Optional[int] = None
    failure: Optional[str]
    headers: Optional[dict]
    elapsed_s: float
    reported: StringBasedDateTime
    json: Optional[dict] = None
    body: Optional[str] = None

    def __init__(self, *args, **kwargs):
        super(ResponseDescription, self).__init__(*args, **kwargs)
        if "headers" not in self:
            self.headers = {}

    @property
    def status_code(self) -> int:
        return self.code or 999

    @property
    def content(self) -> Optional[str]:
        if self.json is not None:
            return json.dumps(self.json)
        else:
            return self.body


yaml.add_representer(ResponseDescription, Representer.represent_dict)


def describe_response(resp: requests.Response) -> ResponseDescription:
    headers = {k: v for k, v in resp.headers.items()}
    kwargs = {
        "code": resp.status_code,
        "headers": headers,
        "elapsed_s": resp.elapsed.total_seconds(),
        "reported": StringBasedDateTime(datetime.datetime.utcnow()),
    }
    try:
        kwargs["json"] = resp.json()
    except ValueError:
        kwargs["body"] = resp.content.decode("utf-8")
    return ResponseDescription(**kwargs)


class Query(ImplicitDict):
    request: RequestDescription
    response: ResponseDescription

    @property
    def status_code(self) -> int:
        return self.response.status_code

    @property
    def json_result(self) -> Optional[Dict]:
        return self.response.json


class QueryError(RuntimeError):
    """Error encountered when interacting with a server in the UTM ecosystem."""

    def __init__(self, msg, queries: Optional[List[Query]] = None):
        super(RuntimeError, self).__init__(msg)
        self.queries = queries or []

    @property
    def stacktrace(self) -> str:
        return "".join(
            traceback.format_exception(
                etype=QueryError, value=self, tb=self.__traceback__
            )
        )


yaml.add_representer(Query, Representer.represent_dict)


def describe_query(resp: requests.Response, initiated_at: datetime.datetime) -> Query:
    return Query(
        request=describe_request(resp.request, initiated_at),
        response=describe_response(resp),
    )


def query_and_describe(
    client: Optional[infrastructure.UTMClientSession], verb: str, url: str, **kwargs
) -> Query:
    """Attempt to perform a query, and the describe the results of that attempt.

    This function should capture all common problems when attempting to send a query and report the problem in the Query
    result rather than raising an exception.

    Args:
        client: UTMClientSession to use, or None to use a default `requests` Session.
        verb: HTTP verb to perform at the specified URL.
        url: URL to query.
        **kwargs: Any keyword arguments that should be applied to the <session>.request method when invoking it.

    Returns:
        Query object describing the request and response/result.
    """
    if client is None:
        utm_session = False
        client = requests.session()
    else:
        utm_session = True
    req_kwargs = kwargs.copy()
    if "timeout" not in req_kwargs:
        req_kwargs["timeout"] = TIMEOUTS

    failures = []
    # Note: retry logic could be attached to the `client` Session by `mount`ing an HTTPAdapter with custom
    # `max_retries`, however we do not want to mutate the provided Session.  Instead, retry only on errors we explicitly
    # consider retryable.
    for attempt in range(ATTEMPTS):
        t0 = datetime.datetime.utcnow()
        try:
            return describe_query(client.request(verb, url, **req_kwargs), t0)
        except (requests.Timeout, urllib3.exceptions.ReadTimeoutError) as e:
            failure_message = f"query_and_describe attempt {attempt + 1} from PID {os.getpid()} to {verb} {url} failed with timeout {type(e).__name__}: {str(e)}"
            logger.warning(failure_message)
            failures.append(failure_message)
        except requests.RequestException as e:
            failure_message = f"query_and_describe attempt {attempt + 1} from PID {os.getpid()} to {verb} {url} failed with non-retryable RequestException {type(e).__name__}: {str(e)}"
            logger.warning(failure_message)
            failures.append(failure_message)

            break
        finally:
            t1 = datetime.datetime.utcnow()

    # Reconstruct request similar to the one in the query (which is not
    # accessible at this point)
    if utm_session:
        req_kwargs = client.adjust_request_kwargs(req_kwargs)
    del req_kwargs["timeout"]
    req = requests.Request(verb, url, **req_kwargs)
    prepped_req = client.prepare_request(req)
    return Query(
        request=describe_request(prepped_req, t0),
        response=ResponseDescription(
            code=None,
            failure="\n".join(failures),
            elapsed_s=(t1 - t0).total_seconds(),
            reported=StringBasedDateTime(t1),
        ),
    )
