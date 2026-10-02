import base64
import json
import os

from implicitdict import StringBasedDateTime
from loguru import logger
from uas_standards.astm.f3548.v21.api import (
    ExchangeRecord,
    ExchangeRecordRecorderRole,
    Time,
    USSLogSet,
)

from monitoring.benchmarker.configurations.artifacts.usslogset import (
    USSLogSetSpecification,
)
from monitoring.benchmarker.reports.analysis import select_operations
from monitoring.benchmarker.reports.report import BenchmarkRunReport
from monitoring.monitorlib.fetch import Query


def _format_headers(
    headers: dict[str, str] | None,
    include_headers: set[str] | None,
    exclude_headers: set[str] | None,
) -> list[str]:
    if not headers:
        return []
    result = []
    for k, v in headers.items():
        if include_headers is not None and k.lower() not in include_headers:
            continue
        if exclude_headers is not None and k.lower() in exclude_headers:
            continue
        result.append(f"{k}: {v}")
    return result


def _make_exchange_record(
    query: Query,
    include_headers: set[str] | None,
    exclude_headers: set[str] | None,
) -> ExchangeRecord:
    if query.request.outgoing:
        req_headers = (
            query.request.headers
            if "headers" in query.request and query.request.headers is not None
            else None
        )
        headers = _format_headers(req_headers, include_headers, exclude_headers)
    else:
        resp_headers = (
            query.response.headers
            if "headers" in query.response and query.response.headers is not None
            else None
        )
        headers = _format_headers(resp_headers, include_headers, exclude_headers)

    record = ExchangeRecord(
        url=query.request.url,
        method=query.request.method,
        headers=headers,
        recorder_role=(
            ExchangeRecordRecorderRole.Client
            if query.request.outgoing
            else ExchangeRecordRecorderRole.Server
        ),
        request_time=Time(value=StringBasedDateTime(query.request.timestamp)),
        response_time=Time(value=StringBasedDateTime(query.response.reported)),
    )

    if "json" in query.request and query.request.json:
        record.request_body = base64.b64encode(
            json.dumps(query.request.json).encode("utf-8")
        ).decode("utf-8")
    elif "content" in query.request and query.request.content:
        record.request_body = base64.b64encode(
            query.request.content.encode("utf-8")
        ).decode("utf-8")

    if "json" in query.response and query.response.json:
        record.response_body = base64.b64encode(
            json.dumps(query.response.json).encode("utf-8")
        ).decode("utf-8")
    elif "content" in query.response and query.response.content:
        record.response_body = base64.b64encode(
            query.response.content.encode("utf-8")
        ).decode("utf-8")

    if "code" in query.response and query.response.code is not None:
        record.response_code = query.response.code

    if "failure" in query.response and query.response.failure is not None:
        record.problem = query.response.failure

    return record


def generate_usslogset(
    report: BenchmarkRunReport, spec: USSLogSetSpecification, output_dir: str
) -> None:
    include_headers = (
        {h.lower() for h in spec.include_headers}
        if "include_headers" in spec and spec.include_headers is not None
        else None
    )
    exclude_headers = (
        {h.lower() for h in spec.exclude_headers}
        if "exclude_headers" in spec and spec.exclude_headers is not None
        else None
    )

    messages: list[ExchangeRecord] = []
    for scenario in report.report.scenarios:
        for ops_by_type in scenario.operations:
            if ops_by_type.type.startswith("query.astm.f3548.v21.dss."):
                for op in select_operations(ops_by_type):
                    if "query" not in op or op.query is None:
                        raise ValueError(
                            f"Operation of type '{ops_by_type.type}' at {op.t0} is missing query details"
                        )
                    messages.append(
                        _make_exchange_record(
                            op.query, include_headers, exclude_headers
                        )
                    )

    log_set = USSLogSet(messages=messages)
    out_path = os.path.join(output_dir, "usslogset.json")
    logger.info(f"Writing USSLogSet artifact ({len(messages)} messages) to {out_path}")
    with open(out_path, "w") as f:
        json.dump(log_set, f, sort_keys=True)
