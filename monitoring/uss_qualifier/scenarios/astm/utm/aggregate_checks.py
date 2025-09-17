import re
from datetime import timedelta

from uas_standards.astm.f3548.v21 import constants
from uas_standards.astm.f3548.v21.constants import (
    ConflictingOIMaxUserNotificationTimeSeconds,
)

from monitoring.monitorlib import fetch
from monitoring.monitorlib.fetch import QueryType, evaluation
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.flight_planning import FlightPlannersResource
from monitoring.uss_qualifier.scenarios.astm.utm.notifications_to_operator import (
    notification_checker,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class AggregateChecks(TestScenario):
    _queries: list[fetch.Query]
    _attributed_queries: dict[ParticipantID, dict[QueryType, list[fetch.Query]]] = {}

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
            flight_planner.participant_id: dict()
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
                    self._attributed_queries[query.participant_id][query.query_type] = (
                        list()
                    )
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

        self.begin_test_case("Notifications to operator")
        self.begin_test_step("Notifications for causing conflicts")
        self._check_notification_latencies(
            context,
            notification_checker.SCD0090_NOTE_PREFIX,
            "Notifications for causing conflicts",
            "Caused-conflict",
            "conflicts caused by the operator",
        )
        self.end_test_step()
        self.begin_test_step("Notifications for observing conflicts")
        self._check_notification_latencies(
            context,
            notification_checker.SCD0095_NOTE_PREFIX,
            "Notifications for observing conflicts",
            "Conflicting flight",
            "conflicts affecting the operator's flights",
        )
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
                        summary="95th percentile of durations for operational intent details requests to USS is higher than threshold",
                        details=f"threshold: {constants.MaxRespondToOIDetailsRequestSeconds}s, 95th percentile: {p95:.3g}s",
                    )

            self.record_note(
                f"{participant}/{QueryType.F3548v21USSGetOperationalIntentDetails}",
                f"checked performances on {len(durations)} queries, 95th percentile: {p95:.3g}s",
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
        participant_queries: dict[QueryType, list[fetch.Query]],
    ):
        # Keep track of how many interactions we've found for this participant
        # if there is None the condition is not met
        test_interactions = 0
        success_by_type: dict[QueryType, bool] = {}
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

    def _check_notification_latencies(
        self,
        context: ExecutionContext,
        prefix: str,
        check_name: str,
        notification_type: str,
        notification_type_long: str,
    ):
        cutoff = timedelta(seconds=ConflictingOIMaxUserNotificationTimeSeconds)
        latencies = _get_latencies(context, prefix)
        for participant_id, latency_list in latencies.items():
            if not latency_list:
                continue
            n_ok = sum(1 if latency < cutoff else 0 for latency in latency_list)
            n_total = len(latency_list)
            with self.check(check_name, participant_id) as check:
                percentage = 100 * n_ok / n_total
                if percentage < 95:
                    check.record_failed(
                        summary=f"{notification_type} notifications delivered {percentage:.1f}% of the time",
                        details=f"The actual delivery rate of {percentage:.2f}% ({n_ok}/{n_total}) for notifications regarding {notification_type_long} does not meet the 95% threshold",
                    )
                else:
                    latency_list.sort()
                    median_latency = latency_list[
                        int((len(latency_list) + 1) / 2)
                    ].total_seconds()
                    self.record_note(
                        f"{participant_id}/{prefix}",
                        f"Median latency >{median_latency:.2f}s, max >{max(latency_list).total_seconds()}s, min >{min(latency_list).total_seconds()}s",
                    )


def _get_latencies(
    context: ExecutionContext, prefix: str
) -> dict[ParticipantID, list[timedelta]]:
    pattern = notification_checker.NOTIFICATION_NOTE_FORMAT.format(
        participant_id="(.*)", latency=r"(\d*\.?\d*)"
    )
    matcher = re.compile(pattern)
    latencies = {}
    for report in context.test_scenario_reports():
        if "notes" not in report or not report.notes:
            continue
        for key, value in report.notes.items():
            if not key.startswith(prefix):
                continue
            m = matcher.match(value.message)
            if not m:
                continue
            participant_id = m.group(1)
            latency_str = m.group(2)
            try:
                latency_s = float(latency_str)
            except ValueError:
                continue
            latency_list = latencies.get(participant_id, [])
            latency_list.append(timedelta(seconds=latency_s))
            latencies[participant_id] = latency_list
    return latencies


def _is_interop_test_interaction(query_type: QueryType):
    return (
        query_type == QueryType.InterUSSFlightPlanningV1GetStatus
        or query_type == QueryType.InterUSSFlightPlanningV1ClearArea
        or query_type == QueryType.InterUSSFlightPlanningV1UpsertFlightPlan
        or query_type == QueryType.InterUSSFlightPlanningV1DeleteFlightPlan
    )
