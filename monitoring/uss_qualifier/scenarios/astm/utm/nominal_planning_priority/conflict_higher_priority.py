from typing import Optional

from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    Capability,
)
from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
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
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    validate_shared_operational_intent,
)
from monitoring.uss_qualifier.scenarios.flight_planning.prioritization_test_steps import (
    activate_priority_conflict_flight_intent,
    plan_priority_conflict_flight_intent,
    modify_planned_priority_conflict_flight_intent,
    modify_activated_priority_conflict_flight_intent,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    clear_area,
    check_capabilities,
    plan_flight_intent,
    cleanup_flights,
    activate_flight_intent,
    delete_flight_intent,
    modify_activated_flight_intent,
)


class ConflictHigherPriority(TestScenario):
    flight_1: FlightIntent
    flight_1_id: Optional[str] = None
    flight_1_op_intent_id: Optional[str] = None
    flight_2: FlightIntent
    flight_2_id: Optional[str] = None
    flight_2_op_intent_id: Optional[str] = None
    uss1: FlightPlanner
    uss2: FlightPlanner
    dss: DSSInstance

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        tested_uss: FlightPlannerResource,
        control_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
    ):
        super().__init__()
        self.uss1 = tested_uss.flight_planner
        self.uss2 = control_uss.flight_planner
        self.dss = dss.dss

        flight_intents = flight_intents.get_flight_intents()
        if len(flight_intents) < 2:
            raise ValueError(
                f"`{self.me()}` TestScenario requires at least 2 flight_intents; found {len(flight_intents)}"
            )

        (self.flight_1, self.flight_2) = flight_intents
        if (
            "activated" not in self.flight_1.mutations
            or "time_range_B" not in self.flight_1.mutations
            or "time_range_A_extended" not in self.flight_1.mutations
            or "activated" not in self.flight_2.mutations
            or "time_range_B" not in self.flight_2.mutations
        ):
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight mutations are not met"
            )

        if (
            self.flight_2.request.operational_intent.priority
            <= self.flight_1.request.operational_intent.priority
        ):
            raise ValueError(
                f"`{self.me()}` TestScenario requires priority flight to be higher priority than the first flight"
            )

    def run(self):
        self.begin_test_scenario()

        self.record_note(
            "Tested USS",
            f"{self.uss1.config.participant_id}",
        )
        self.record_note(
            "Control USS",
            f"{self.uss2.config.participant_id}",
        )

        self.begin_test_case("Setup")
        if not self._setup():
            return
        self.end_test_case()

        self.begin_test_case("Attempt to plan flight in conflict")
        self._attempt_plan_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to modify planned flight in conflict")
        self._attempt_modify_planned_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to activate flight in conflict")
        self._attempt_activate_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Modify activated flight with pre-existing conflict")
        self._modify_activated_flight_conflict_preexisting()
        self.end_test_case()

        self.begin_test_case("Attempt to modify activated flight in conflict")
        self._attempt_modify_activated_flight_conflict()
        self.end_test_case()

        self.end_test_scenario()

    def _setup(self) -> bool:
        if not check_capabilities(
            self,
            "Check for necessary capabilities",
            required_capabilities=[
                (
                    [self.uss1, self.uss2],
                    Capability.BasicStrategicConflictDetection,
                )
            ],
            prerequisite_capabilities=[(self.uss2, Capability.HighPriorityFlights)],
        ):
            return False

        clear_area(
            self,
            "Area clearing",
            [self.flight_1, self.flight_2],
            [self.uss1, self.uss2],
        )

        return True

    def _attempt_plan_flight_conflict(self):
        resp_flight_2, self.flight_2_id = plan_flight_intent(
            self, "Plan flight 2", self.uss2, self.flight_2.request
        )
        self.flight_2_op_intent_id = resp_flight_2.operational_intent_id

        _ = plan_priority_conflict_flight_intent(
            self,
            "Attempt to plan flight 1",
            self.uss1,
            self.flight_1.request,
        )

        validate_shared_operational_intent(
            self,
            "Validate flight 2 sharing",
            self.flight_2.request,
            self.flight_2_op_intent_id,
        )

        # TODO: add validation test step that op intent for flight 1 was not created

    def _attempt_modify_planned_flight_conflict(self):
        _ = delete_flight_intent(self, "Delete flight 2", self.uss2, self.flight_2_id)
        self.flight_2_id = None
        self.flight_2_op_intent_id = None

        resp_flight_1, self.flight_1_id = plan_flight_intent(
            self, "Plan flight 1", self.uss1, self.flight_1.request
        )
        self.flight_1_op_intent_id = resp_flight_1.operational_intent_id

        resp_flight_2, self.flight_2_id = plan_flight_intent(
            self, "Plan flight 2", self.uss2, self.flight_2.request
        )
        self.flight_2_op_intent_id = resp_flight_2.operational_intent_id

        flight_1_modified = self.flight_1.get_mutated("time_range_A_extended")
        _ = modify_planned_priority_conflict_flight_intent(
            self,
            "Attempt to modify planned flight 1 in conflict",
            self.uss1,
            self.flight_1_id,
            flight_1_modified.request,
        )

        validate_shared_operational_intent(
            self,
            "Validate flight 1 sharing",
            self.flight_1.request,
            self.flight_1_op_intent_id,
        )
        validate_shared_operational_intent(
            self,
            "Validate flight 2 sharing",
            self.flight_2.request,
            self.flight_2_op_intent_id,
        )

    def _attempt_activate_flight_conflict(self):
        flight_1_activated = self.flight_1.get_mutated("activated")
        _ = activate_priority_conflict_flight_intent(
            self,
            "Attempt to activate conflicting flight 1",
            self.uss1,
            self.flight_1_id,
            flight_1_activated.request,
        )

        validate_shared_operational_intent(
            self,
            "Validate flight 1 sharing",
            self.flight_1.request,
            self.flight_1_op_intent_id,
        )

    def _modify_activated_flight_conflict_preexisting(self):
        _ = delete_flight_intent(self, "Delete flight 2", self.uss2, self.flight_2_id)
        self.flight_2_id = None
        self.flight_2_op_intent_id = None

        flight_1_activated = self.flight_1.get_mutated("activated")
        _ = activate_flight_intent(
            self,
            "Activate flight 1",
            self.uss1,
            self.flight_1_id,
            flight_1_activated.request,
        )

        resp_flight_2, self.flight_2_id = plan_flight_intent(
            self, "Plan flight 2", self.uss2, self.flight_2.request
        )
        self.flight_2_op_intent_id = resp_flight_2.operational_intent_id

        flight_2_activated = self.flight_2.get_mutated("activated")
        _ = activate_flight_intent(
            self,
            "Activate flight 2",
            self.uss2,
            self.flight_2_id,
            flight_2_activated.request,
        )

        flight_1_modified = flight_1_activated.get_mutated("time_range_A_extended")
        _ = modify_activated_flight_intent(
            self,
            "Modify activated flight 1 in conflict with activated flight 2",
            self.uss1,
            self.flight_1_id,
            flight_1_modified.request,
        )

        validate_shared_operational_intent(
            self,
            "Validate flight 1 sharing",
            flight_1_modified.request,
            self.flight_1_op_intent_id,
        )
        validate_shared_operational_intent(
            self,
            "Validate flight 2 sharing",
            flight_2_activated.request,
            self.flight_2_op_intent_id,
        )

    def _attempt_modify_activated_flight_conflict(self):
        flight_2_modified = self.flight_2.get_mutated("activated").get_mutated(
            "time_range_B"
        )
        _ = modify_activated_flight_intent(
            self,
            "Modify activated flight 2 to not conflict with activated flight 1",
            self.uss2,
            self.flight_2_id,
            flight_2_modified.request,
        )

        flight_1_activated = self.flight_1.get_mutated("activated")
        flight_1_modified = flight_1_activated.get_mutated("time_range_B")
        _ = modify_activated_priority_conflict_flight_intent(
            self,
            "Attempt to modify activated flight 1 in conflict",
            self.uss1,
            self.flight_1_id,
            flight_1_modified.request,
        )

        validate_shared_operational_intent(
            self,
            "Validate flight 1 sharing",
            flight_1_activated.request,
            self.flight_1_op_intent_id,
        )
        validate_shared_operational_intent(
            self,
            "Validate flight 2 sharing",
            flight_2_modified.request,
            self.flight_2_op_intent_id,
        )

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.uss2, self.uss1))
        self.end_cleanup()
