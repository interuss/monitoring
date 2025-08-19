import base64

from implicitdict import StringBasedDateTime
from uas_standards.astm.f3548.v21.api import (
    ExchangeRecord,
    ExchangeRecordRecorderRole,
    OperationalIntentDetails,
    Time,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import Query

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


def make_exchange_record(query: Query, msg_problem: str) -> ExchangeRecord:
    def str_headers(headers: dict[str, str] | None) -> list[str]:
        if headers is None:
            return []
        return [f"{h_name}: {h_val}" for h_name, h_val in headers.items()]

    er = ExchangeRecord(
        url=query.request.url,
        method=query.request.method,
        headers=str_headers(query.request.headers)
        + str_headers(query.response.headers),
        recorder_role=(
            ExchangeRecordRecorderRole.Client
            if query.request.outgoing
            else ExchangeRecordRecorderRole.Server
        ),
        request_time=Time(value=StringBasedDateTime(query.request.timestamp)),
        response_time=Time(value=StringBasedDateTime(query.response.reported)),
        response_code=query.status_code,
        problem=msg_problem,
    )

    if query.request.content is not None:
        er.request_body = base64.b64encode(
            query.request.content.encode("utf-8")
        ).decode("utf-8")
    if query.response.content is not None:
        er.response_body = base64.b64encode(
            query.response.content.encode("utf-8")
        ).decode("utf-8")

    return er
