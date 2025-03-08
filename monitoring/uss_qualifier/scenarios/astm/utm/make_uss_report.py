from typing import Dict

import arrow
from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.astm.f3548.v21 import constants
from uas_standards.astm.f3548.v21.api import (
    OPERATIONS,
    ErrorReport,
    ExchangeRecord,
    ExchangeRecordRecorderRole,
    GetOperationalIntentDetailsResponse,
    OperationID,
    Time,
)

from monitoring.monitorlib.fetch import Query, QueryError, QueryType, query_and_describe
from monitoring.monitorlib.infrastructure import AuthAdapter, UTMClientSession
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.scenarios.astm.utm import FlightIntentValidation
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class MakeUssReport(TestScenario):
    _auth: AuthAdapter

    def __init__(
        self,
        utm_auth: AuthAdapterResource,
    ):
        super().__init__()
        utm_auth.assert_scopes_available(
            scopes_required={
                constants.Scope.StrategicCoordination: "call makeUssReport as a USS"
            },
            consumer_name=f"{self.__class__.__name__} test scenario",
        )
        self._auth = utm_auth.adapter

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.begin_test_case("Call makeUssReport interface")
        self.begin_test_step("Identify USS base URLs")
        base_urls = self._get_uss_base_urls(context)
        self.end_test_step()

        if base_urls:
            self.begin_test_step("Call makeUssReport interfaces")
            self._call_make_uss_report(base_urls)
            self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _get_uss_base_urls(self, context: ExecutionContext) -> Dict[str, ParticipantID]:
        base_urls_by_participant = {}
        for report in context.find_test_scenario_reports(FlightIntentValidation):
            cases = [
                case
                for case in report.cases
                if case.name == "Validate transition to Ended state after cancellation"
            ]
            for case in cases:
                steps = [
                    step for step in case.steps if step.name == "Plan Valid Flight"
                ]
                for step in steps:
                    checks = [
                        check
                        for check in step.passed_checks
                        if check.name == "Operational intent details data format"
                    ]
                    if checks:
                        base_urls = []
                        for query in step.queries:
                            if (
                                query.query_type
                                == QueryType.F3548v21USSGetOperationalIntentDetails
                            ):
                                try:
                                    resp = query.parse_json_result(
                                        GetOperationalIntentDetailsResponse
                                    )
                                except QueryError:
                                    continue
                                base_urls.append(
                                    resp.operational_intent.reference.uss_base_url
                                )
                        if len(base_urls) > 1:
                            raise RuntimeError(
                                f"Found {len(base_urls)} sets of operational intent details in test scenario '{report.name}' started at {report.start_time} with base URLs {', '.join(base_urls)}"
                            )
                        if base_urls:
                            participant_ids = []
                            for check in checks:
                                for participant_id in check.participants:
                                    if participant_id not in participant_ids:
                                        participant_ids.append(participant_id)
                            if len(participant_ids) > 1:
                                raise RuntimeError(
                                    f"Found {len(participant_ids)} participant IDs associated with checks in '{step.name}' test step in test scenario '{report.name}' started at {report.start_time}: {', '.join(participant_ids)}"
                                )
                            if participant_ids:
                                base_urls_by_participant[base_urls[0]] = (
                                    participant_ids[0]
                                )

        return base_urls_by_participant

    def _call_make_uss_report(self, base_urls: Dict[str, ParticipantID]) -> None:
        for base_url, participant_id in base_urls.items():
            client = UTMClientSession(base_url, self._auth)
            url = base_url + OPERATIONS[OperationID.MakeUssReport].path
            t = StringBasedDateTime(arrow.utcnow())
            exchange = ExchangeRecord(
                url=url,
                method="GET",
                recorder_role=ExchangeRecordRecorderRole.Client,
                request_time=Time(value=t),
                problem="this is a dummy record created by the USS qualifier. This failure is expected.",
            )
            with self.check(
                "makeUssReport responds correctly", participant_id
            ) as check:
                try:
                    query = _make_uss_report(client, participant_id, exchange)
                    if query.status_code != 201:
                        raise QueryError(
                            f"Received code {query.status_code} when attempting to make USS report{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                            query,
                        )
                except QueryError as e:
                    for query in e.queries:
                        self.record_query(query)
                    check.record_failed(
                        summary="Error querying makeUssReport",
                        details=e.msg,
                        query_timestamps=[q.timestamp for q in e.queries],
                    )
                    continue
                self.record_query(query)

                try:
                    resp = ImplicitDict.parse(query.response.json, ErrorReport)
                except (ValueError, TypeError, KeyError) as e:
                    check.record_failed(
                        summary="Error parsing makeUssReport response",
                        details=f"{type(e).__name__}: {e.msg}",
                        query_timestamps=[query.timestamp],
                    )
                    continue

                if "report_id" not in resp or not resp.report_id:
                    check.record_failed(
                        summary="report_id not populated",
                        details="The report_id field was not populated in the response to makeUssReport",
                        query_timestamps=[query.timestamp],
                    )
                    continue


def _make_uss_report(
    client: UTMClientSession, participant_id: ParticipantID, exchange: ExchangeRecord
) -> Query:
    req = ErrorReport(exchange=exchange)
    op = OPERATIONS[OperationID.MakeUssReport]
    return query_and_describe(
        client,
        op.verb,
        op.path,
        QueryType.F3548v21USSMakeUssReport,
        participant_id,
        scope=constants.Scope.StrategicCoordination,
        json=req,
    )
