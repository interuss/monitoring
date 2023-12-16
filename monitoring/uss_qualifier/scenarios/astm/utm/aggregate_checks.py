from typing import List, Dict

from uas_standards.astm.f3548.v21 import constants

from monitoring.monitorlib import fetch
from monitoring.monitorlib.fetch import evaluation, QueryType
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.flight_planning import FlightPlannersResource
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


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

        self.begin_test_case("Interoperability test instance is available")
        self.begin_test_step("Interoperability test instance is available")

        self._confirm_test_harness_queries_work()

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
                        details=f"threshold: {constants.MaxRespondToOIDetailsRequestSeconds}s, 95th percentile: {p95}s",
                    )

            self.record_note(
                f"{participant}/{QueryType.F3548v21USSGetOperationalIntentDetails}",
                f"checked performances on {len(durations)} queries, 95th percentile: {p95}s",
            )

    def _confirm_test_harness_queries_work(self):
        """
        For each different type of call to the interoperability test instance,
        we look for at least one successful query.
        """
        for participant, queries_by_type in self._attributed_queries.items():
            self._validate_participant_test_interop_instance(
                participant, queries_by_type
            )

    def _validate_participant_test_interop_instance(
        self,
        participant_id: str,
        participant_queries: dict[QueryType, List[fetch.Query]],
    ):
        # Keep track of how many interactions we've found for this participant
        # if there is None the condition is not met
        test_interactions = 0
        success_by_type: Dict[QueryType, bool] = {}
        for query_type, queries in participant_queries.items():
            if _is_interop_test_interaction(query_type):
                test_interactions += len(queries)
                success_by_type[query_type] = False
                for query in queries:
                    if 200 <= query.response.status_code < 300:
                        success_by_type[query_type] = True
                        break

        self.record_note(
            "test_interop_interactions",
            f"Found {test_interactions} interactions with interoperability test instance for {participant_id}",
        )
        if test_interactions == 0:
            self.record_note(
                "test_interop_check_skipped",
                f"Skipping check for {participant_id} because no interactions with "
                f"interoperability test instance were found",
            )
            # If no interactions are observed, we can't determine if the test instance is available
            # and the step here.
            return

        with self.check(
            "Interoperability test instance is available", [participant_id]
        ) as check:
            for query_type, success in success_by_type.items():
                if not success:
                    check.record_failed(
                        summary=f"No successful {query_type} interaction with interoperability test instance",
                        details=f"Found no successful {query_type} interaction with interoperability test instance, "
                        f"indicating that the test instance is either not available or not properly implemented.",
                    )


def _is_interop_test_interaction(query_type: QueryType):
    return (
        query_type == QueryType.InterUSSFlightPlanningV1GetStatus
        or query_type == QueryType.InterUSSFlightPlanningV1ClearArea
        or query_type == QueryType.InterUSSFlightPlanningV1UpsertFlightPlan
        or query_type == QueryType.InterUSSFlightPlanningV1DeleteFlightPlan
    )
