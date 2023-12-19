from typing import List

from monitoring.monitorlib.fetch import QueryError
from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightResponseResult,
)
from monitoring.monitorlib.uspace import problems_with_flight_authorisation
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntent,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlanner,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerResource,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    plan_flight_intent,
    cleanup_flights,
)


class Validation(TestScenario):
    invalid_flight_intents: List[FlightIntent]
    valid_flight_intent: FlightIntent
    ussp: FlightPlanner

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        flight_planner: FlightPlannerResource,
    ):
        super().__init__()
        self.ussp = flight_planner.flight_planner

        intents = flight_intents.get_flight_intents()
        if len(intents) < 2 or "valid_flight_auth" not in intents:
            raise ValueError(
                f"`{self.me()}` TestScenario requires at least 2 flight_intents and valid_flight_auth; found {len(intents)}"
            )

        self.invalid_flight_intents = []
        for fID, info_template in intents.items():
            flight_intent = FlightIntent.from_flight_info_template(info_template)
            problems = problems_with_flight_authorisation(
                flight_intent.request.flight_authorisation
            )

            if fID == "valid_flight_auth":
                self.valid_flight_intent = flight_intent
                if problems:
                    problems = ", ".join(problems)
                    raise ValueError(
                        f"`{self.me()}` TestScenario requires valid_flight_auth to be valid.  Instead, the flight authorisation data had: {problems}"
                    )

            else:
                self.invalid_flight_intents.append(flight_intent)
                if not problems:
                    raise ValueError(
                        f"`{self.me()}` TestScenario requires all flight intents except the last to have invalid flight authorisation data.  Instead, intent {fID} had valid flight authorisation data."
                    )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.record_note("Planner", self.ussp.participant_id)

        self.begin_test_case("Attempt invalid flights")
        if not self._attempt_invalid_flights():
            return
        self.end_test_case()

        self.begin_test_case("Plan valid flight")
        self.begin_test_step("Plan valid flight intent")
        if not self._plan_valid_flight():
            return
        self.end_test_step()
        self.end_test_case()

        self.end_test_scenario()

    def _attempt_invalid_flights(self) -> bool:
        self.begin_test_step("Inject invalid flight intents")

        for flight_intent in self.invalid_flight_intents:
            with self.check("Failure", [self.ussp.participant_id]) as failure_check:
                try:
                    resp, query, flight_id, _ = self.ussp.request_flight(
                        flight_intent.request
                    )
                except QueryError as e:
                    for q in e.queries:
                        self.record_query(q)
                    check.record_failed(
                        summary=f"Error from {self.ussp.participant_id} when attempting to inject invalid flight",
                        severity=Severity.High,
                        details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                        query_timestamps=[q.request.timestamp for q in e.queries],
                    )
                self.record_query(query)

                with self.check(
                    "Incorrectly planned", [self.ussp.participant_id]
                ) as check:
                    if resp.result == InjectFlightResponseResult.Planned:
                        problems = ", ".join(
                            problems_with_flight_authorisation(
                                flight_intent.request.flight_authorisation
                            )
                        )
                        check.record_failed(
                            summary="Flight planned with invalid flight authorisation",
                            severity=Severity.Medium,
                            details=f"Flight intent resulted in successful flight planning even though the flight authorisation had: {problems}",
                            query_timestamps=[query.request.timestamp],
                        )

                if resp.result == InjectFlightResponseResult.Failed:
                    failure_check.record_failed(
                        summary="Failed to create flight",
                        severity=Severity.Medium,
                        details=f'{self.ussp.participant_id} Failed to process the user flight intent: "{resp.notes}"',
                        query_timestamps=[query.request.timestamp],
                    )

            self.end_test_step()  # Inject flight intents

        return True

    def _plan_valid_flight(self) -> bool:
        resp, _, _ = plan_flight_intent(
            self,
            self.ussp,
            self.valid_flight_intent.request,
        )
        if resp is None:
            return False

        return True

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, [self.ussp])
        self.end_cleanup()
