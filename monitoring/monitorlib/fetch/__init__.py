import datetime
import json
import traceback
from typing import Dict, Optional, List

import arrow
import flask
import requests
import urllib3
import yaml
from yaml.representer import Representer

from monitoring.monitorlib import infrastructure


TIMEOUTS = (5, 25)  # Timeouts of `connect` and `read` in seconds


def coerce(obj: Dict, desired_type: type):
    if isinstance(obj, desired_type):
        return obj
    else:
        return desired_type(obj)


class RequestDescription(dict):
    @property
    def token(self) -> Dict:
        return infrastructure.get_token_claims(self.get("headers", {}))

    @property
    def timestamp(self) -> datetime.datetime:
        if "initiated_at" in self:
            # This was an outgoing request
            return arrow.get(self["initiated_at"]).datetime
        elif "received_at" in self:
            # This was an incoming request
            return arrow.get(self["received_at"]).datetime
        else:
            raise KeyError(
                "RequestDescription missing both initiated_at and received_at"
            )


yaml.add_representer(RequestDescription, Representer.represent_dict)


def describe_flask_request(request: flask.Request) -> RequestDescription:
    headers = {k: v for k, v in request.headers}
    info = {
        "method": request.method,
        "url": request.url,
        "received_at": datetime.datetime.utcnow().isoformat(),
        "headers": headers,
    }
    try:
        info["json"] = request.json
    except ValueError:
        info["body"] = request.data.encode("utf-8")
    return RequestDescription(info)


def describe_request(
    req: requests.PreparedRequest, initiated_at: datetime.datetime
) -> RequestDescription:
    headers = {k: v for k, v in req.headers.items()}
    info = {
        "method": req.method,
        "url": req.url,
        "initiated_at": initiated_at.isoformat(),
        "headers": headers,
    }
    body = req.body.decode("utf-8") if req.body else None
    try:
        if body:
            info["json"] = json.loads(body)
        else:
            info["body"] = body
    except ValueError:
        info["body"] = body
    return RequestDescription(info)


class ResponseDescription(dict):
    @property
    def status_code(self) -> int:
        return self["code"] if self.get("code") is not None else 999

    @property
    def reported(self) -> datetime.datetime:
        return arrow.get(self["reported"]).datetime


yaml.add_representer(ResponseDescription, Representer.represent_dict)


def describe_response(resp: requests.Response) -> ResponseDescription:
    headers = {k: v for k, v in resp.headers.items()}
    info = {
        "code": resp.status_code,
        "headers": headers,
        "elapsed_s": resp.elapsed.total_seconds(),
        "reported": datetime.datetime.utcnow().isoformat(),
    }
    try:
        info["json"] = resp.json()
    except ValueError:
        info["body"] = resp.content.decode("utf-8")
    return ResponseDescription(info)


class Query(dict):
    @property
    def request(self) -> RequestDescription:
        return coerce(self["request"], RequestDescription)

    @property
    def response(self) -> ResponseDescription:
        return coerce(self["response"], ResponseDescription)

    @property
    def status_code(self) -> int:
        return self.response.status_code

    @property
    def json_result(self) -> Optional[Dict]:
        return self.response.get("json", None)


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
        {
            "request": describe_request(resp.request, initiated_at),
            "response": describe_response(resp),
        }
    )


def query_and_describe(
    client: infrastructure.UTMClientSession, method: str, url: str, **kwargs
) -> Query:
    req_kwargs = kwargs.copy()
    req_kwargs["timeout"] = TIMEOUTS
    t0 = datetime.datetime.utcnow()
    try:
        return describe_query(client.request(method, url, **req_kwargs), t0)
    except (requests.RequestException, urllib3.exceptions.ReadTimeoutError) as e:
        msg = "{}: {}".format(type(e).__name__, str(e))
    t1 = datetime.datetime.utcnow()

    # Reconstruct request similar to the one in the query (which is not
    # accessible at this point)
    del req_kwargs["timeout"]
    req_kwargs = client.adjust_request_kwargs(req_kwargs)
    req = requests.Request(method, url, **req_kwargs)
    prepped_req = client.prepare_request(req)
    return Query(
        {
            "request": describe_request(prepped_req, t0),
            "response": ResponseDescription(
                {
                    "code": None,
                    "failure": msg,
                    "elapsed_s": (t1 - t0).total_seconds(),
                    "reported": t1,
                }
            ),
        }
    )
