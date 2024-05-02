from datetime import timedelta
from typing import Dict

import arrow
from implicitdict import StringBasedTimeDelta

from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
    FlightInfo,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    FlightPlanStatus,
    PlanningActivityResult,
)
from monitoring.monitorlib.temporal import TimeDuringTest, Time
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.astm.f3548.v21.constants import (
    Scope,
    TimeSyncMaxDifferentialSeconds,
    OiMaxPlanHorizonDays,
)

from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerResource,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    OpIntentValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    submit_flight,
    plan_flight,
    delete_flight,
    cleanup_flights,
)


class FlightIntentValidation(TestScenario):

    times: Dict[TimeDuringTest, Time]

    valid_flight: FlightInfoTemplate
    valid_activated: FlightInfoTemplate

    invalid_too_far_away: FlightInfoTemplate
    invalid_recently_ended: FlightInfoTemplate

    valid_conflict_tiny_overlap: FlightInfoTemplate

    tested_uss: FlightPlannerClient
    dss: DSSInstance

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        tested_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
    ):
        super().__init__()
        self.tested_uss = tested_uss.client
        self.dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "search for operational intent references to verify outcomes of planning activities"
            }
        )

        expected_flight_intents = [
            ExpectedFlightIntent(
                "valid_flight",
                "Valid Flight",
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "valid_activated",
                "Valid Flight",
                usage_state=AirspaceUsageState.InUse,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "valid_conflict_tiny_overlap",
                "Tiny Overlap Conflict Flight",
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
                must_conflict_with=["Valid Flight"],
            ),
            ExpectedFlightIntent(
                "invalid_too_far_away",
                "Too Far Away Flight",
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
                time_start_min_bound=StringBasedTimeDelta(
                    timedelta(days=OiMaxPlanHorizonDays)
                ),
            ),
            ExpectedFlightIntent(
                "invalid_recently_ended",
                "Recently Ended Flight",
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
                time_end_min_bound=StringBasedTimeDelta(
                    timedelta(seconds=-TimeSyncMaxDifferentialSeconds - 5)
                ),
                time_end_max_bound=StringBasedTimeDelta(
                    timedelta(seconds=-TimeSyncMaxDifferentialSeconds)
                ),
            ),
        ]

        templates = flight_intents.get_flight_intents()
        try:
            validate_flight_intent_templates(templates, expected_flight_intents)
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

        for efi in expected_flight_intents:
            setattr(self, efi.intent_id, templates[efi.intent_id])

    def resolve_flight(self, flight_template: FlightInfoTemplate) -> FlightInfo:
        self.times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        return flight_template.resolve(self.times)

    def run(self, context: ExecutionContext):
        self.times = {
            TimeDuringTest.StartOfTestRun: Time(context.start_time),
            TimeDuringTest.StartOfScenario: Time(arrow.utcnow().datetime),
        }

        self.begin_test_scenario(context)
        self.record_note(
            "Tested USS",
            f"{self.tested_uss.participant_id}",
        )

        self.begin_test_case("Attempt to plan invalid flights")
        self._attempt_invalid()
        self.end_test_case()

        self.begin_test_case("Validate transition to Ended state after cancellation")
        self._validate_ended_cancellation()
        self.end_test_case()

        self.begin_test_case("Validate precision of intersection computations")
        self._validate_precision_intersection()
        self.end_test_case()

        self.end_test_scenario()

    def _attempt_invalid(self):
        self.begin_test_step("Attempt to plan Too Far Away Flight")
        invalid_too_far_away = self.resolve_flight(self.invalid_too_far_away)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            invalid_too_far_away,
        ) as validator:
            submit_flight(
                scenario=self,
                success_check="Incorrectly planned",
                expected_results={
                    (PlanningActivityResult.Rejected, FlightPlanStatus.NotPlanned)
                },
                failed_checks={PlanningActivityResult.Failed: "Failure"},
                flight_planner=self.tested_uss,
                flight_info=invalid_too_far_away,
            )

            validator.expect_not_shared()
        self.end_test_step()

        self.begin_test_step("Attempt to plan Recently Ended Flight")
        invalid_recently_ended = self.resolve_flight(self.invalid_recently_ended)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            invalid_recently_ended,
        ) as validator:
            submit_flight(
                scenario=self,
                success_check="Incorrectly planned",
                expected_results={
                    (PlanningActivityResult.Rejected, FlightPlanStatus.NotPlanned)
                },
                failed_checks={PlanningActivityResult.Failed: "Failure"},
                flight_planner=self.tested_uss,
                flight_info=invalid_recently_ended,
                may_end_in_past=True,
            )

            validator.expect_not_shared()
        self.end_test_step()

    def _validate_ended_cancellation(self):
        self.begin_test_step("Plan Valid Flight")
        valid_flight = self.resolve_flight(self.valid_flight)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            valid_flight,
        ) as planned_validator:
            _, flight_id = plan_flight(
                self,
                self.tested_uss,
                valid_flight,
            )
            oi_ref = planned_validator.expect_shared(valid_flight)
        self.end_test_step()

        self.begin_test_step("Remove Valid Flight")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            valid_flight,
        ) as cancelled_validator:
            _ = delete_flight(self, self.tested_uss, flight_id)
            cancelled_validator.expect_removed(oi_ref.id)
        self.end_test_step()

    def _validate_precision_intersection(self):
        self.begin_test_step("Plan Valid Flight")
        valid_flight = self.resolve_flight(self.valid_flight)

        plan_flight(
            self,
            self.tested_uss,
            valid_flight,
        )
        self.end_test_step()

        self.begin_test_step("Attempt to plan Tiny Overlap Conflict Flight")
        valid_conflict_tiny_overlap = self.resolve_flight(
            self.valid_conflict_tiny_overlap
        )

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            valid_conflict_tiny_overlap,
        ) as validator:
            submit_flight(
                scenario=self,
                success_check="Incorrectly planned",
                expected_results={
                    (PlanningActivityResult.Rejected, FlightPlanStatus.NotPlanned)
                },
                failed_checks={PlanningActivityResult.Failed: "Failure"},
                flight_planner=self.tested_uss,
                flight_info=valid_conflict_tiny_overlap,
            )

            validator.expect_not_shared()
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, [self.tested_uss])
        self.end_cleanup()
