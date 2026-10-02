import base64

from implicitdict import StringBasedDateTime
from uas_standards.astm.f3548.v21.api import (
    ExchangeRecord,
    ExchangeRecordRecorderRole,
    OperationalIntentDetails,
    Time,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import Query, RequestDescription

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# API version 0.3.17 is programmatically identical to version 1.0.0, so both these versions can be used interchangeably.
API_1_0_0 = "1.0.0"
API_0_3_17 = API_1_0_0

SCOPE_SC = Scope.StrategicCoordination
SCOPE_CM = Scope.ConstraintManagement
SCOPE_CP = Scope.ConstraintProcessing
SCOPE_CM_SA = Scope.ConformanceMonitoringForSituationalAwareness
SCOPE_AA = Scope.AvailabilityArbitration

NO_OVN_PHRASES = {"", "Available from USS"}


def priority_of(details: OperationalIntentDetails) -> int:
    priority = 0
    if "priority" in details and details.priority:
        priority = details.priority
    return priority


def _str_headers(
    headers: dict[str, str] | None, include_headers: set[str] | None = None
) -> list[str]:
    if headers is None:
        return []
    if include_headers is not None:
        allowed = {h.lower() for h in include_headers}
        return [
            f"{h_name}: {h_val}"
            for h_name, h_val in headers.items()
            if h_name.lower() in allowed
        ]
    return [f"{h_name}: {h_val}" for h_name, h_val in headers.items()]


def make_request_exchange_record(
    request: RequestDescription, include_headers: set[str] | None = None
) -> ExchangeRecord:
    req_headers = (
        request.headers
        if "headers" in request and request.headers is not None
        else None
    )
    er = ExchangeRecord(
        url=request.url,
        method=request.method,
        headers=_str_headers(req_headers, include_headers),
        recorder_role=(
            ExchangeRecordRecorderRole.Client
            if request.outgoing
            else ExchangeRecordRecorderRole.Server
        ),
        request_time=Time(value=StringBasedDateTime(request.timestamp)),
    )
    if request.content is not None:
        er.request_body = base64.b64encode(request.content.encode("utf-8")).decode(
            "utf-8"
        )
    return er


def make_exchange_record(
    query: Query,
    msg_problem: str | None = None,
    include_headers: set[str] | None = None,
) -> ExchangeRecord:
    er = make_request_exchange_record(query.request, include_headers=include_headers)
    resp_headers = (
        query.response.headers
        if "headers" in query.response and query.response.headers is not None
        else None
    )
    er.headers = (er.headers or []) + _str_headers(resp_headers, include_headers)
    er.response_time = Time(value=StringBasedDateTime(query.response.reported))
    er.response_code = query.status_code
    if msg_problem is not None:
        er.problem = msg_problem
    elif "failure" in query.response and query.response.failure is not None:
        er.problem = query.response.failure

    if query.response.content is not None:
        er.response_body = base64.b64encode(
            query.response.content.encode("utf-8")
        ).decode("utf-8")

    return er
