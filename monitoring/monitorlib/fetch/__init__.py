import datetime
import json
import os
import traceback
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar
from urllib.parse import urlparse

import flask
import jwt
import requests
import urllib3
import yaml
from implicitdict import ImplicitDict, StringBasedDateTime
from loguru import logger
from yaml.representer import Representer

from monitoring.monitorlib import infrastructure
from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.rid import RIDVersion


@dataclass
class Settings:
    connect_timeout_seconds: float | None = 3.1
    """Number of seconds to allow for establishing a connection."""

    read_timeout_seconds: float | None = 6.1
    """Number of seconds to allow for a request to complete after establishing a connection."""

    attempts: int = 2
    """Number of attempts to query when experiencing a retryable error like a timeout"""

    add_request_id: bool = True
    """Whether to automatically add a `request_id` field to any request with a JSON body and no pre-existing `request_id` field"""

    fake_netlocs: tuple[str] = ("testdummy.interuss.org",)
    """Network locations well-known to be fake and for which a request should fail immediately without being attempted."""


settings = Settings()
"""Singleton settings for queries made with this tool"""


class RequestDescription(ImplicitDict):
    method: str
    url: str
    headers: dict | None
    json: dict | None = None
    body: str | None = None

    initiated_at: StringBasedDateTime | None
    received_at: StringBasedDateTime | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "headers" not in self:
            self.headers = {}

    @property
    def token(self) -> dict:
        return infrastructure.get_token_claims(self.headers)

    @property
    def timestamp(self) -> datetime.datetime:
        if self.outgoing:
            return self.initiated_at.datetime
        else:
            return self.received_at.datetime

    @property
    def outgoing(self) -> bool:
        if "initiated_at" in self:
            # This was an outgoing request
            return True
        elif "received_at" in self:
            # This was an incoming request
            return False
        else:
            raise KeyError(
                "RequestDescription missing both initiated_at and received_at"
            )

    @property
    def url_hostname(self) -> str:
        return urlparse(self.url).hostname

    @property
    def content(self) -> str | None:
        if self.json is not None:
            return json.dumps(self.json)
        else:
            return self.body


yaml.add_representer(RequestDescription, Representer.represent_dict)


def describe_flask_request(request: flask.Request) -> RequestDescription:
    headers = {k: v for k, v in request.headers}
    kwargs = {
        "method": request.method,
        "url": request.url,
        "received_at": StringBasedDateTime(datetime.datetime.now(datetime.UTC)),
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
    code: int | None = None
    failure: str | None
    headers: dict | None
    elapsed_s: float
    reported: StringBasedDateTime
    json: dict | None = None
    body: str | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "headers" not in self:
            self.headers = {}

    @property
    def status_code(self) -> int:
        return self.code or 999

    @property
    def content(self) -> str | None:
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
        "reported": StringBasedDateTime(datetime.datetime.now(datetime.UTC)),
    }
    try:
        kwargs["json"] = resp.json()
    except ValueError:
        kwargs["body"] = resp.content.decode("utf-8")
    return ResponseDescription(**kwargs)


def describe_aiohttp_response(
    status: int, headers: dict, resp_json: dict, duration: datetime.timedelta
) -> ResponseDescription:
    kwargs = {
        "code": status,
        "headers": headers,
        "elapsed_s": duration.total_seconds(),
        "reported": StringBasedDateTime(datetime.datetime.now(datetime.UTC)),
        "json": resp_json,
    }

    return ResponseDescription(**kwargs)


def describe_failed_aiohttp_response(
    exception: Exception, duration: datetime.timedelta
) -> ResponseDescription:
    kwargs = {
        "failure": str(exception),
        "elapsed_s": duration.total_seconds(),
        "reported": StringBasedDateTime(datetime.datetime.now(datetime.UTC)),
    }

    return ResponseDescription(**kwargs)


def describe_flask_response(resp: flask.Response, elapsed_s: float):
    headers = {k: v for k, v in resp.headers.items()}
    kwargs = {
        "code": resp.status_code,
        "headers": headers,
        "reported": StringBasedDateTime(datetime.datetime.now(datetime.UTC)),
        "elapsed_s": elapsed_s,
    }
    try:
        kwargs["json"] = resp.get_json()
    except ValueError:
        kwargs["body"] = resp.get_data(as_text=True)
    return ResponseDescription(**kwargs)


class QueryType(str, Enum):
    # ASTM F3411-19 and F3411-22a (RID)
    # DSS endpoints
    F3411v19DSSSearchIdentificationServiceAreas = (
        "astm.f3411.v19.dss.searchIdentificationServiceAreas"
    )
    F3411v22aDSSSearchIdentificationServiceAreas = (
        "astm.f3411.v22a.dss.searchIdentificationServiceAreas"
    )

    F3411v19DSSGetIdentificationServiceArea = (
        "astm.f3411.v19.dss.getIdentificationServiceArea"
    )
    F3411v22aDSSGetIdentificationServiceArea = (
        "astm.f3411.v22a.dss.getIdentificationServiceArea"
    )

    F3411v19DSSCreateIdentificationServiceArea = (
        "astm.f3411.v19.dss.createIdentificationServiceArea"
    )
    F3411v22aDSSCreateIdentificationServiceArea = (
        "astm.f3411.v22a.dss.createIdentificationServiceArea"
    )

    F3411v19DSSUpdateIdentificationServiceArea = (
        "astm.f3411.v19.dss.updateIdentificationServiceArea"
    )
    F3411v22aDSSUpdateIdentificationServiceArea = (
        "astm.f3411.v22a.dss.updateIdentificationServiceArea"
    )

    F3411v19DSSDeleteIdentificationServiceArea = (
        "astm.f3411.v19.dss.deleteIdentificationServiceArea"
    )
    F3411v22aDSSDeleteIdentificationServiceArea = (
        "astm.f3411.v22a.dss.deleteIdentificationServiceArea"
    )

    F3411v19DSSSearchSubscriptions = "astm.f3411.v19.dss.searchSubscriptions"
    F3411v22aDSSSearchSubscriptions = "astm.f3411.v22a.dss.searchSubscriptions"

    F3411v19DSSGetSubscription = "astm.f3411.v19.dss.getSubscription"
    F3411v22aDSSGetSubscription = "astm.f3411.v22a.dss.getSubscription"

    F3411v19DSSCreateSubscription = "astm.f3411.v19.dss.createSubscription"
    F3411v22aDSSCreateSubscription = "astm.f3411.v22a.dss.createSubscription"

    F3411v19DSSUpdateSubscription = "astm.f3411.v19.dss.updateSubscription"
    F3411v22aDSSUpdateSubscription = "astm.f3411.v22a.dss.updateSubscription"

    F3411v19DSSDeleteSubscription = "astm.f3411.v19.dss.deleteSubscription"
    F3411v22aDSSDeleteSubscription = "astm.f3411.v22a.dss.deleteSubscription"

    # USS endpoints
    F3411v19USSSearchFlights = "astm.f3411.v19.uss.searchFlights"
    F3411v22aUSSSearchFlights = "astm.f3411.v22a.uss.searchFlights"

    F3411v19USSPostIdentificationServiceArea = (
        "astm.f3411.v19.uss.postIdentificationServiceArea"
    )
    F3411v22aUSSPostIdentificationServiceArea = (
        "astm.f3411.v22a.uss.postIdentificationServiceArea"
    )

    F3411v22aUSSGetFlightDetails = "astm.f3411.v22a.uss.getFlightDetails"
    F3411v19USSGetFlightDetails = "astm.f3411.v19.uss.getFlightDetails"

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

    # InterUSS automated testing geospatial_map interface
    InterUSSGeospatialMapV1QueryGeospatialMap = (
        "interuss.automated_testing.geospatial_map.v1.QueryGeospatialMap"
    )

    # InterUSS RID observation interface
    InterUSSRIDObservationV1GetDisplayData = (
        "interuss.automated_testing.rid.v1.observation.getDisplayData"
    )
    InterUSSRIDObservationV1GetDetails = (
        "interuss.automated_testing.rid.v1.observation.getDetails"
    )

    # Flight injection (test harness)
    InterussRIDAutomatedTestingV1CreateTest = (
        "interuss.automated_testing.rid.v1.injection.createTest"
    )

    InterussRIDAutomatedTestingV1DeleteTest = (
        "interuss.automated_testing.rid.v1.injection.deleteTest"
    )

    InterussRIDAutomatedTestingV1UserNotifications = (
        "interuss.automated_testing.rid.v1.injection.UserNotifications"
    )

    # InterUSS mock_uss
    InterUSSMockUSSGetLogs = "interuss.mock_uss.logging.interaction_logs"
    InterUSSMockUSSGetLocality = "interuss.mock_uss.locality.locality_get"
    InterUSSMockUSSSetLocality = "interuss.mock_uss.locality.locality_set"

    # Deprecated InterUSS SCD injection API
    InterUSSSCDInjectionV1GetStatus = "interuss.deprecated_scd_injection.v1.getStatus"
    InterUSSSCDInjectionV1InjectFlight = (
        "interuss.deprecated_scd_injection.v1.injectFlight"
    )
    InterUSSSCDInjectionV1DeleteFlight = (
        "interuss.deprecated_scd_injection.v1.deleteFlight"
    )
    InterUSSSCDInjectionV1ClearArea = "interuss.deprecated_scd_injection.v1.clearArea"

    def __str__(self):
        return self.value

    @staticmethod
    def dss_get_isa(rid_version: RIDVersion):
        if rid_version == RIDVersion.f3411_19:
            return QueryType.F3411v19DSSGetIdentificationServiceArea
        elif rid_version == RIDVersion.f3411_22a:
            return QueryType.F3411v22aDSSGetIdentificationServiceArea
        else:
            raise ValueError(f"Unsupported RID version: {rid_version}")

    @staticmethod
    def dss_create_isa(rid_version: RIDVersion):
        if rid_version == RIDVersion.f3411_19:
            return QueryType.F3411v19DSSCreateIdentificationServiceArea
        elif rid_version == RIDVersion.f3411_22a:
            return QueryType.F3411v22aDSSCreateIdentificationServiceArea
        else:
            raise ValueError(f"Unsupported RID version: {rid_version}")

    @staticmethod
    def dss_update_isa(rid_version: RIDVersion):
        if rid_version == RIDVersion.f3411_19:
            return QueryType.F3411v19DSSUpdateIdentificationServiceArea
        elif rid_version == RIDVersion.f3411_22a:
            return QueryType.F3411v22aDSSUpdateIdentificationServiceArea
        else:
            raise ValueError(f"Unsupported RID version: {rid_version}")

    @staticmethod
    def dss_delete_isa(rid_version: RIDVersion):
        if rid_version == RIDVersion.f3411_19:
            return QueryType.F3411v19DSSDeleteIdentificationServiceArea
        elif rid_version == RIDVersion.f3411_22a:
            return QueryType.F3411v22aDSSDeleteIdentificationServiceArea
        else:
            raise ValueError(f"Unsupported RID version: {rid_version}")


ResponseType = TypeVar("ResponseType", bound=ImplicitDict)


class Query(ImplicitDict):
    request: RequestDescription
    response: ResponseDescription

    participant_id: str | None
    """If specified, identifier of the USS/participant hosting the server involved in this query."""

    query_type: QueryType | None
    """If specified, the recognized type of this query."""

    @property
    def timestamp(self) -> datetime.datetime:
        """Safety property to prevent crashes when Query.timestamp is accessed.
        For intentional access, request.timestamp should be used instead."""
        return self.request.timestamp

    @property
    def status_code(self) -> int:
        return self.response.status_code

    @property
    def json_result(self) -> dict | None:
        return self.response.json

    @property
    def error_message(self) -> str | None:
        return (
            self.json_result["message"]
            if self.json_result is not None and "message" in self.json_result
            else None
        )

    @property
    def failure_details(self) -> str | None:
        """
        Returns the error message if one is available, otherwise returns the response content.
        To be used to fill in the details of a check failure.
        Note that 'failure' here is context dependent: possibly a 401 is expected and a 404 or 200 is returned,
        in both situations we would like to return the most relevant information.
        """
        err_msg = self.error_message
        if err_msg:
            return err_msg
        return self.response.json

    def get_client_sub(self):
        headers = self.request.headers
        if "Authorization" in headers:
            token = headers.get("Authorization").split(" ")[1]
            payload = jwt.decode(
                token, algorithms="RS256", options={"verify_signature": False}
            )
            return payload["sub"]

    def parse_json_result(self, parse_type: type[ResponseType]) -> ResponseType:
        """Parses the JSON result into the specified type.

        Args:
            parse_type: ImplicitDict type to parse into.
        Returns:
             the parsed response (of type `parse_type`).
        Raises:
            * QueryError: if the parsing failed.
        """
        try:
            return parse_type(ImplicitDict.parse(self.response.json, parse_type))
        except (ValueError, TypeError, KeyError) as e:
            raise QueryError(
                f"Parsing JSON response into type {parse_type.__name__} failed with exception {type(e).__name__}: {e}",
                self,
            )


class QueryError(RuntimeError):
    """Error encountered when interacting with a server in the UTM ecosystem.
    This error will usually wrap one query that failed and that caused the error,
    and may be accompanied by additional queries for context."""

    queries: list[Query]

    def __init__(self, msg: str, queries: Query | list[Query] | None = None):
        """
        Args:
            msg: description of the error
            queries: 0, one or multiple queries related to the error. If multiple queries are provided,
            the first one in the list should be the main cause of the error.
        """
        super().__init__(msg)
        self.msg = msg
        if queries is None:
            self.queries = []
        elif isinstance(queries, Query):
            self.queries = [queries]
        else:
            self.queries = queries

    @property
    def cause_status_code(self) -> int:
        """Returns the status code of the query that caused this error,
        or 999 if this error contains no queries."""
        if len(self.queries) == 0:
            return 999
        return self.queries[0].status_code

    @property
    def query_timestamps(self) -> list[datetime.datetime]:
        """Returns the timestamps of all queries present in this QueryError."""
        return [q.request.timestamp for q in self.queries]

    @property
    def cause(self) -> Query | None:
        """Returns the query that caused this error."""
        if len(self.queries) == 0:
            return None
        return self.queries[0]

    @property
    def stacktrace(self) -> str:
        return stacktrace_string(self)


yaml.add_representer(Query, Representer.represent_dict)

yaml.add_representer(StringBasedDateTime, Representer.represent_str)


def describe_query(
    resp: requests.Response,
    initiated_at: datetime.datetime,
    query_type: QueryType | None = None,
    participant_id: str | None = None,
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
    client: infrastructure.UTMClientSession | None,
    verb: str,
    url: str,
    query_type: QueryType | None = None,
    participant_id: str | None = None,
    expect_failure: bool = False,
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
        expect_failure: If true, do not print warning messages upon failures because they are expected.
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
        req_kwargs["timeout"] = (
            settings.connect_timeout_seconds,
            settings.read_timeout_seconds,
        )

    # Attach a request_id field to the JSON body of any outgoing request with a JSON body that doesn't already have one
    if (
        settings.add_request_id
        and "json" in req_kwargs
        and isinstance(req_kwargs["json"], dict)
        and "request_id" not in req_kwargs["json"]
    ):
        json_body = json.loads(json.dumps(req_kwargs["json"]))
        json_body["request_id"] = str(uuid.uuid4())
        req_kwargs["json"] = json_body

    failures = []

    is_netloc_fake = False
    try:
        is_netloc_fake = urlparse(url).netloc in settings.fake_netlocs
    except ValueError:
        pass

    def get_location() -> str:
        return (
            traceback.format_list([traceback.extract_stack()[-3]])[0]
            .split("\n")[0]
            .strip()
        )

    # Note: retry logic could be attached to the `client` Session by `mount`ing an HTTPAdapter with custom
    # `max_retries`, however we do not want to mutate the provided Session.  Instead, retry only on errors we explicitly
    # consider retryable.
    for attempt in range(settings.attempts):
        t0 = datetime.datetime.now(datetime.UTC)
        try:
            if is_netloc_fake:
                failure_message = f"query_and_describe attempt {attempt + 1} from PID {os.getpid()} to {verb} {url} was not attempted because network location of {url} was identified as fake: {settings.fake_netlocs}\nAt {get_location()}"
                failures.append(failure_message)
                break

            return describe_query(
                client.request(verb, url, **req_kwargs),
                t0,
                query_type=query_type,
                participant_id=participant_id,
            )
        except (requests.Timeout, urllib3.exceptions.ReadTimeoutError) as e:
            failure_message = f"query_and_describe attempt {attempt + 1} from PID {os.getpid()} to {verb} {url} failed with timeout {type(e).__name__}: {str(e)}\nAt {get_location()}"
            if not expect_failure:
                logger.warning(failure_message)
            failures.append(failure_message)
        except requests.ConnectionError as e:
            if "RemoteDisconnected" in str(e):
                # This error manifests as:
                #   ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
                # ...and this may be retryable
                retryable = True
            else:
                retryable = False
            failure_message = f"query_and_describe attempt {attempt + 1} from PID {os.getpid()} to {verb} {url} failed with {'' if retryable else 'non-'}retryable ConnectionError: {str(e)}\nAt {get_location()}"
            if not expect_failure:
                logger.warning(failure_message)
            failures.append(failure_message)
            if not retryable:
                break
        except requests.RequestException as e:
            failure_message = f"query_and_describe attempt {attempt + 1} from PID {os.getpid()} to {verb} {url} failed with non-retryable RequestException {type(e).__name__}: {str(e)}\nAt {get_location()}"
            if not expect_failure:
                logger.warning(failure_message)
            failures.append(failure_message)

            break
        finally:
            t1 = datetime.datetime.now(datetime.UTC)

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
