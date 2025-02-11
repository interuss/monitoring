from typing import Dict, List

import arrow

from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    FlightInfo,
    UasState,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    FlightPlanStatus,
    PlanningActivityResult,
)
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.uss_qualifier.resources.flight_planning import FlightIntentsResource
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerResource,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    cleanup_flights,
    plan_flight,
    submit_flight,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class Validation(TestScenario):
    times: Dict[TimeDuringTest, Time]

    invalid_flight_intents: List[FlightInfoTemplate]
    valid_flight_intent: FlightInfoTemplate
    ussp: FlightPlannerClient

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        flight_planner: FlightPlannerResource,
    ):
        super().__init__()
        self.ussp = flight_planner.client

        templates = flight_intents.get_flight_intents()
        expected_flight_intents = [
            ExpectedFlightIntent(
                "valid_flight_auth",
                "Valid Flight",
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
                valid_uspace_flight_auth=True,
            )
        ]
        for intent_id, flight_template in templates.items():
            if intent_id.startswith("invalid_"):
                expected_flight_intents.append(
                    ExpectedFlightIntent(
                        intent_id,
                        f"Invalid Flight {intent_id}",
                        usage_state=AirspaceUsageState.Planned,
                        uas_state=UasState.Nominal,
                        valid_uspace_flight_auth=False,
                    )
                )

        try:
            if len(expected_flight_intents) < 2:
                raise ValueError(
                    f"`{self.me()}` TestScenario requires at least 2 flight_intents; found {len(expected_flight_intents)}"
                )
            validate_flight_intent_templates(templates, expected_flight_intents)
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

        self.invalid_flight_intents = []
        for efi in expected_flight_intents:
            if efi.intent_id == "valid_flight_auth":
                self.valid_flight_intent = templates[efi.intent_id]
            else:
                self.invalid_flight_intents.append(templates[efi.intent_id])

    def resolve_flight(self, flight_template: FlightInfoTemplate) -> FlightInfo:
        self.times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        return flight_template.resolve(self.times)

    def run(self, context: ExecutionContext):
        self.times = {
            TimeDuringTest.StartOfTestRun: Time(context.start_time),
            TimeDuringTest.StartOfScenario: Time(arrow.utcnow().datetime),
        }

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

        for flight_intent_template in self.invalid_flight_intents:
            flight_intent = self.resolve_flight(flight_intent_template)

            resp, _ = submit_flight(
                scenario=self,
                success_check="Incorrectly planned",
                expected_results={
                    (PlanningActivityResult.Rejected, FlightPlanStatus.NotPlanned),
                },
                failed_checks={PlanningActivityResult.Failed: "Failure"},
                flight_planner=self.ussp,
                flight_info=flight_intent,
            )

        self.end_test_step()  # Inject flight intents

        return True

    def _plan_valid_flight(self) -> bool:
        valid_flight_intent = self.resolve_flight(self.valid_flight_intent)

        resp, _ = plan_flight(
            self,
            self.ussp,
            valid_flight_intent,
        )
        if resp is None:
            return False

        return True

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, [self.ussp])
        self.end_cleanup()
