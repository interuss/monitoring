from typing import Dict, List

import arrow
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    OperationalIntentReference,
)
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    PlanningActivityResult,
    FlightPlanStatus,
)
from monitoring.monitorlib.temporal import TimeDuringTest, Time
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
)

from monitoring.uss_qualifier.scenarios.astm.utm import DownUSS
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    OpIntentValidator,
    set_uss_down,
    set_uss_available,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    submit_flight,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class DownUSSEqualPriorityNotPermitted(DownUSS):
    flight2_planned: FlightInfoTemplate

    @property
    def _expected_flight_intents(self) -> List[ExpectedFlightIntent]:
        return [
            ExpectedFlightIntent(
                "flight2_planned",
                "Flight 2",
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            )
        ]

    def run(self, context: ExecutionContext):
        self.times = {
            TimeDuringTest.StartOfTestRun: Time(context.start_time),
            TimeDuringTest.StartOfScenario: Time(arrow.utcnow().datetime),
        }

        self.begin_test_scenario(context)

        self.record_note(
            "Tested USS",
            f"{self.tested_uss.config.participant_id}",
        )

        self.begin_test_case("Setup")
        self._setup()
        self.end_test_case()

        self.begin_test_case(
            "Plan Flight 2 in conflict with activated operational intent managed by down USS"
        )
        oi_ref = self._plan_flight_conflict_activated()
        self.end_test_case()

        self.begin_test_case(
            "Plan Flight 2 in conflict with nonconforming operational intent managed by down USS"
        )
        oi_ref = self._plan_flight_conflict_nonconforming(oi_ref)
        self.end_test_case()

        self.begin_test_case(
            "Plan Flight 2 in conflict with contingent operational intent managed by down USS"
        )
        self._plan_flight_conflict_contingent(oi_ref)
        self.end_test_case()

        self.end_test_scenario()

    def _plan_flight_conflict_activated(self) -> OperationalIntentReference:

        # Virtual USS creates conflicting operational intent test step
        flight2_planned = self.resolve_flight(self.flight2_planned)
        oi_ref = self._put_conflicting_op_intent_step(
            flight2_planned, OperationalIntentState.Accepted
        )

        # Virtual USS activates conflicting operational intent test step
        oi_ref = self._put_conflicting_op_intent_step(
            flight2_planned, OperationalIntentState.Activated, oi_ref
        )

        # Declare virtual USS as down at DSS test step
        self.begin_test_step("Declare virtual USS as down at DSS")
        set_uss_down(self, self.dss, self.uss_qualifier_sub)
        self.end_test_step()

        # Tested USS attempts to plan high-priority flight 2 test step
        self.begin_test_step("Tested USS attempts to plan high-priority Flight 2")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            flight2_planned,
        ) as validator:
            submit_flight(
                scenario=self,
                success_check="Incorrectly planned",
                expected_results={
                    (PlanningActivityResult.Rejected, FlightPlanStatus.NotPlanned),
                },
                failed_checks={PlanningActivityResult.Failed: "Failure"},
                flight_planner=self.tested_uss.client,
                flight_info=flight2_planned,
            )

            validator.expect_not_shared()
        self.end_test_step()

        # Restore virtual USS availability at DSS test step
        self.begin_test_step("Restore virtual USS availability at DSS")
        set_uss_available(self, self.dss, self.uss_qualifier_sub)
        self.end_test_step()

        return oi_ref

    def _plan_flight_conflict_nonconforming(
        self, oi_ref: OperationalIntentReference
    ) -> OperationalIntentReference:

        # Virtual USS transitions to Nonconforming conflicting operational intent test step
        flight2_planned = self.resolve_flight(self.flight2_planned)
        oi_ref = self._put_conflicting_op_intent_step(
            flight2_planned, OperationalIntentState.Nonconforming, oi_ref
        )

        # Declare virtual USS as down at DSS test step
        self.begin_test_step("Declare virtual USS as down at DSS")
        set_uss_down(self, self.dss, self.uss_qualifier_sub)
        self.end_test_step()

        # Tested USS attempts to plan high-priority flight 2 test step
        self.begin_test_step("Tested USS attempts to plan high-priority Flight 2")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            flight2_planned,
        ) as validator:
            submit_flight(
                scenario=self,
                success_check="Incorrectly planned",
                expected_results={
                    (PlanningActivityResult.Rejected, FlightPlanStatus.NotPlanned),
                },
                failed_checks={PlanningActivityResult.Failed: "Failure"},
                flight_planner=self.tested_uss.client,
                flight_info=flight2_planned,
            )

            validator.expect_not_shared()
        self.end_test_step()

        # Restore virtual USS availability at DSS test step
        self.begin_test_step("Restore virtual USS availability at DSS")
        set_uss_available(self, self.dss, self.uss_qualifier_sub)
        self.end_test_step()

        return oi_ref

    def _plan_flight_conflict_contingent(self, oi_ref: OperationalIntentReference):

        # Virtual USS transitions to Contingent conflicting operational intent test step
        flight2_planned = self.resolve_flight(self.flight2_planned)
        self._put_conflicting_op_intent_step(
            flight2_planned, OperationalIntentState.Contingent, oi_ref
        )

        # Declare virtual USS as down at DSS test step
        self.begin_test_step("Declare virtual USS as down at DSS")
        set_uss_down(self, self.dss, self.uss_qualifier_sub)
        self.end_test_step()

        # Tested USS attempts to plan high-priority flight 2 test step
        self.begin_test_step("Tested USS attempts to plan high-priority Flight 2")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            flight2_planned,
        ) as validator:
            submit_flight(
                scenario=self,
                success_check="Incorrectly planned",
                expected_results={
                    (PlanningActivityResult.Rejected, FlightPlanStatus.NotPlanned),
                },
                failed_checks={PlanningActivityResult.Failed: "Failure"},
                flight_planner=self.tested_uss.client,
                flight_info=flight2_planned,
            )

            validator.expect_not_shared()
        self.end_test_step()
