import datetime
import json
import os
import traceback
import uuid
import jwt
from typing import Dict, Optional, List, Union

from enum import Enum
from urllib.parse import urlparse

import aiohttp
import flask
from loguru import logger
import requests
import urllib3
import yaml
from yaml.representer import Representer

from implicitdict import ImplicitDict, StringBasedDateTime
from monitoring.monitorlib import infrastructure
from monitoring.monitorlib.rid import RIDVersion

TIMEOUTS = (5, 5)  # Timeouts of `connect` and `read` in seconds
ATTEMPTS = (
    2  # Number of attempts to query when experiencing a retryable error like a timeout
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

    @property
    def url_hostname(self) -> str:
        return urlparse(self.url).hostname


yaml.add_representer(RequestDescription, Representer.represent_dict)


def describe_flask_request(request: flask.Request) -> RequestDescription:
    headers = {k: v for k, v in request.headers}
    kwargs = {
        "method": request.method,
        "url": request.url,
        "received_at": StringBasedDateTime(datetime.datetime.utcnow()),
        "headers": headers,
    }
    data = request.data.decode("utf-8")
    if request.is_json:
        try:
            kwargs["json"] = json.loads(data)
        except ValueError:
            kwargs["body"] = data
    else:
        kwargs["body"] = data
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


def describe_aiohttp_response(
    status: int, headers: Dict, resp_json: Dict, duration: datetime.timedelta
) -> ResponseDescription:
    kwargs = {
        "code": status,
        "headers": headers,
        "elapsed_s": duration.total_seconds(),
        "reported": StringBasedDateTime(datetime.datetime.utcnow()),
        "json": resp_json,
    }

    return ResponseDescription(**kwargs)


def describe_flask_response(resp: flask.Response, elapsed_s: float):
    headers = {k: v for k, v in resp.headers.items()}
    kwargs = {
        "code": resp.status_code,
        "headers": headers,
        "reported": StringBasedDateTime(datetime.datetime.utcnow()),
        "elapsed_s": elapsed_s,
    }
    try:
        kwargs["json"] = resp.get_json()
    except ValueError:
        kwargs["body"] = resp.get_data(as_text=True)
    return ResponseDescription(**kwargs)


class QueryType(str, Enum):
    F3411v22aFlights = "astm.f3411.v22a.sp.flights"
    F3411v19Flights = "astm.f3411.v19.sp.flights"
    F3411v22aFlightDetails = "astm.f3411.v22a.sp.flight_details"
    F3411v19aFlightDetails = "astm.f3411.v19.sp.flight_details"

    # ASTM F3548-21
    F3548v21DSSQueryOperationalIntentReferences = (
        "astm.f3548.v21.dss.queryOperationalIntentReferences"
    )
    F3548v21DSSGetOperationalIntentReference = (
        "astm.f3548.v21.dss.getOperationalIntentReference"
    )
    F3548v21DSSCreateOperationalIntentReference = (
        "astm.f3548.v21.dss.createOperationalIntentReference"
    )
    F3548v21DSSUpdateOperationalIntentReference = (
        "astm.f3548.v21.dss.updateOperationalIntentReference"
    )
    F3548v21DSSDeleteOperationalIntentReference = (
        "astm.f3548.v21.dss.deleteOperationalIntentReference"
    )
    F3548v21DSSQueryConstraintReferences = (
        "astm.f3548.v21.dss.queryConstraintReferences"
    )
    F3548v21DSSGetConstraintReference = "astm.f3548.v21.dss.getConstraintReference"
    F3548v21DSSCreateConstraintReference = (
        "astm.f3548.v21.dss.createConstraintReference"
    )
    F3548v21DSSUpdateConstraintReference = (
        "astm.f3548.v21.dss.updateConstraintReference"
    )
    F3548v21DSSDeleteConstraintReference = (
        "astm.f3548.v21.dss.deleteConstraintReference"
    )
    F3548v21DSSQuerySubscriptions = "astm.f3548.v21.dss.querySubscriptions"
    F3548v21DSSGetSubscription = "astm.f3548.v21.dss.getSubscription"
    F3548v21DSSCreateSubscription = "astm.f3548.v21.dss.createSubscription"
    F3548v21DSSUpdateSubscription = "astm.f3548.v21.dss.updateSubscription"
    F3548v21DSSDeleteSubscription = "astm.f3548.v21.dss.deleteSubscription"
    F3548v21DSSMakeDssReport = "astm.f3548.v21.dss.makeDssReport"
    F3548v21DSSSetUssAvailability = "astm.f3548.v21.uss.setUssAvailability"
    F3548v21DSSGetUssAvailability = "astm.f3548.v21.uss.getUssAvailability"
    F3548v21USSGetOperationalIntentDetails = (
        "astm.f3548.v21.uss.getOperationalIntentDetails"
    )
    F3548v21USSGetOperationalIntentTelemetry = (
        "astm.f3548.v21.uss.getOperationalIntentTelemetry"
    )
    F3548v21USSNotifyOperationalIntentDetailsChanged = (
        "astm.f3548.v21.uss.notifyOperationalIntentDetailsChanged"
    )
    F3548v21USSGetConstraintDetails = "astm.f3548.v21.uss.getConstraintDetails"
    F3548v21USSNotifyConstraintDetailsChanged = (
        "astm.f3548.v21.uss.notifyConstraintDetailsChanged"
    )
    F3548v21USSMakeUssReport = "astm.f3548.v21.uss.makeUssReport"

    # InterUSS automated testing versioning interface
    InterUSSVersioningGetVersion = "interuss.automated_testing.versioning.GetVersion"

    # InterUSS automated testing flight_planning interface
    InterUSSFlightPlanningV1GetStatus = (
        "interuss.automated_testing.flight_planning.v1.GetStatus"
    )
    InterUSSFlightPlanningV1ClearArea = (
        "interuss.automated_testing.flight_planning.v1.ClearArea"
    )
    InterUSSFlightPlanningV1UpsertFlightPlan = (
        "interuss.automated_testing.flight_planning.v1.UpsertFlightPlan"
    )
    InterUSSFlightPlanningV1DeleteFlightPlan = (
        "interuss.automated_testing.flight_planning.v1.DeleteFlightPlan"
    )

    @staticmethod
    def flight_details(rid_version: RIDVersion):
        if rid_version == RIDVersion.f3411_19:
            return QueryType.F3411v19aFlightDetails
        elif rid_version == RIDVersion.f3411_22a:
            return QueryType.F3411v22aFlightDetails
        else:
            raise ValueError(f"Unsupported RID version: {rid_version}")


class Query(ImplicitDict):
    request: RequestDescription
    response: ResponseDescription

    participant_id: Optional[str]
    """If specified, identifier of the USS/participant hosting the server involved in this query."""

    query_type: Optional[QueryType]
    """If specified, the recognized type of this query."""

    @property
    def status_code(self) -> int:
        return self.response.status_code

    @property
    def json_result(self) -> Optional[Dict]:
        return self.response.json

    @property
    def error_message(self) -> Optional[str]:
        return (
            self.json_result["message"]
            if self.json_result is not None and "message" in self.json_result
            else None
        )

    def get_client_sub(self):
        headers = self.request.headers
        if "Authorization" in headers:
            token = headers.get("Authorization").split(" ")[1]
            payload = jwt.decode(
                token, algorithms="RS256", options={"verify_signature": False}
            )
            return payload["sub"]


class QueryError(RuntimeError):
    """Error encountered when interacting with a server in the UTM ecosystem."""

    queries: List[Query]

    def __init__(self, msg: str, queries: Optional[Union[Query, List[Query]]] = None):
        super(QueryError, self).__init__(msg)
        self.msg = msg
        if queries is None:
            self.queries = []
        elif isinstance(queries, Query):
            self.queries = [queries]
        else:
            self.queries = queries

    @property
    def stacktrace(self) -> str:
        return "".join(traceback.format_exception(self))


yaml.add_representer(Query, Representer.represent_dict)

yaml.add_representer(StringBasedDateTime, Representer.represent_str)


def describe_query(
    resp: requests.Response,
    initiated_at: datetime.datetime,
    query_type: Optional[QueryType] = None,
    participant_id: Optional[str] = None,
) -> Query:
    query = Query(
        request=describe_request(resp.request, initiated_at),
        response=describe_response(resp),
    )
    if query_type is not None:
        query.query_type = query_type
    if participant_id is not None:
        query.participant_id = participant_id
    return query


def query_and_describe(
    client: Optional[infrastructure.UTMClientSession],
    verb: str,
    url: str,
    query_type: Optional[QueryType] = None,
    participant_id: Optional[str] = None,
    **kwargs,
) -> Query:
    """Attempt to perform a query, and then describe the results of that attempt.

    This function should capture all common problems when attempting to send a query and report the problem in the Query
    result rather than raising an exception.

    Args:
        client: UTMClientSession to use, or None to use a default `requests` Session.
        verb: HTTP verb to perform at the specified URL.
        url: URL to query.
        query_type: If specified, the known type of query that this is.
        participant_id: If specified, the participant identifier of the server being queried.
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

    # Attach a request_id field to the JSON body of any outgoing request with a JSON body that doesn't already have one
    if (
        "json" in req_kwargs
        and isinstance(req_kwargs["json"], dict)
        and "request_id" not in req_kwargs["json"]
    ):
        json_body = json.loads(json.dumps(req_kwargs["json"]))
        json_body["request_id"] = str(uuid.uuid4())
        req_kwargs["json"] = json_body

    failures = []
    # Note: retry logic could be attached to the `client` Session by `mount`ing an HTTPAdapter with custom
    # `max_retries`, however we do not want to mutate the provided Session.  Instead, retry only on errors we explicitly
    # consider retryable.
    for attempt in range(ATTEMPTS):
        t0 = datetime.datetime.utcnow()
        try:
            return describe_query(
                client.request(verb, url, **req_kwargs),
                t0,
                query_type=query_type,
                participant_id=participant_id,
            )
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
    result = Query(
        request=describe_request(prepped_req, t0),
        response=ResponseDescription(
            code=None,
            failure="\n".join(failures),
            elapsed_s=(t1 - t0).total_seconds(),
            reported=StringBasedDateTime(t1),
        ),
        participant_id=participant_id,
    )
    if query_type is not None:
        result.query_type = query_type
    return result


def describe_flask_query(
    req: flask.Request, res: flask.Response, elapsed_s: float
) -> Query:
    return Query(
        request=describe_flask_request(req),
        response=describe_flask_response(res, elapsed_s),
    )
