from typing import List, Dict

from monitoring.monitorlib import fetch
from monitoring.monitorlib.fetch import evaluation, QueryType
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.flight_planning import FlightPlannersResource
from monitoring.uss_qualifier.suites.suite import ExecutionContext

from uas_standards.astm.f3548.v21 import constants

from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class AggregateChecks(TestScenario):

    _queries: List[fetch.Query]
    _attributed_queries: Dict[ParticipantID, Dict[QueryType, List[fetch.Query]]] = {}

    def __init__(
        self,
        flight_planners: FlightPlannersResource,
    ):
        super().__init__()
        self.flight_planners = flight_planners

    def _init_queries(self, context: ExecutionContext):
        self._queries = list(context.sibling_queries())

        # collect and classify queries by participant, only participants part of flight_planners are considered
        self._attributed_queries = {
            flight_planner.flight_planner.participant_id: dict()
            for flight_planner in self.flight_planners.flight_planners
        }
        for query in self._queries:
            if not query.has_field_with_value(
                "participant_id"
            ) or not query.has_field_with_value("query_type"):
                continue

            if query.participant_id in self._attributed_queries:
                if (
                    query.query_type
                    not in self._attributed_queries[query.participant_id]
                ):
                    self._attributed_queries[query.participant_id][
                        query.query_type
                    ] = list()
                self._attributed_queries[query.participant_id][query.query_type].append(
                    query
                )

    def run(self, context: ExecutionContext):
        self._init_queries(context)
        self.begin_test_scenario(context)

        self.record_note("all_queries", f"{len(self._queries)}")
        for participant, queries_by_type in self._attributed_queries.items():
            self.record_note(
                f"{participant}/attributed_queries",
                ", ".join(
                    [
                        f"{query_type}: {len(queries)}"
                        for query_type, queries in queries_by_type.items()
                    ]
                ),
            )

        self.begin_test_case("Performance of SCD requests to USS")
        self.begin_test_step(
            "Performance of successful operational intent details requests"
        )

        self._op_intent_details_step()

        self.end_test_step()
        self.end_test_case()

        self.end_test_scenario()

    def _op_intent_details_step(self):
        for participant, queries_by_type in self._attributed_queries.items():
            if (
                QueryType.F3548v21USSGetOperationalIntentDetails not in queries_by_type
                or len(
                    queries_by_type[QueryType.F3548v21USSGetOperationalIntentDetails]
                )
                == 0
            ):
                self.record_note(
                    f"{participant}/{QueryType.F3548v21USSGetOperationalIntentDetails}",
                    "skipped check: no relevant queries",
                )
                continue

            queries = [
                query
                for query in queries_by_type[
                    QueryType.F3548v21USSGetOperationalIntentDetails
                ]
                if query.response.status_code == 200
            ]
            durations = [query.response.elapsed_s for query in queries]
            [p95] = evaluation.compute_percentiles(durations, [95])
            with self.check(
                "Operational intent details requests take no more than [MaxRespondToOIDetailsRequest] second 95% of the time",
                [participant],
            ) as check:
                if p95 > constants.MaxRespondToOIDetailsRequestSeconds:
                    check.record_failed(
                        summary=f"95th percentile of durations for operational intent details requests to USS is higher than threshold",
                        severity=Severity.Medium,
                        participants=[participant],
                        details=f"threshold: {constants.MaxRespondToOIDetailsRequestSeconds}s, 95th percentile: {p95}s",
                    )

            self.record_note(
                f"{participant}/{QueryType.F3548v21USSGetOperationalIntentDetails}",
                f"checked performances on {len(durations)} queries, 95th percentile: {p95}s",
            )
