from typing import Optional

from uas_standards.astm.f3548.v21.api import OperationalIntentState

from monitoring.monitorlib import scd
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
    ValidateNotSharedOperationalIntent,
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
    flight_1_id: Optional[str] = None
    flight_1_planned_time_range_A: FlightIntent
    flight_1_planned_time_range_A_extended: FlightIntent
    flight_1_activated_time_range_A: FlightIntent
    flight_1_activated_time_range_A_extended: FlightIntent
    flight_1_activated_time_range_B: FlightIntent

    flight_2_id: Optional[str] = None
    flight_2_planned_time_range_A: FlightIntent
    flight_2_activated_time_range_A: FlightIntent
    flight_2_activated_time_range_B: FlightIntent

    tested_uss: FlightPlanner
    control_uss: FlightPlanner
    dss: DSSInstance

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        tested_uss: FlightPlannerResource,
        control_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
    ):
        super().__init__()
        self.tested_uss = tested_uss.flight_planner
        self.control_uss = control_uss.flight_planner
        self.dss = dss.dss

        flight_intents = flight_intents.get_flight_intents()
        try:
            (
                self.flight_1_planned_time_range_A,
                self.flight_1_planned_time_range_A_extended,
                self.flight_1_activated_time_range_A,
                self.flight_1_activated_time_range_A_extended,
                self.flight_1_activated_time_range_B,
                self.flight_2_planned_time_range_A,
                self.flight_2_activated_time_range_A,
                self.flight_2_activated_time_range_B,
            ) = (
                flight_intents["flight_1_planned_time_range_A"],
                flight_intents["flight_1_planned_time_range_A_extended"],
                flight_intents["flight_1_activated_time_range_A"],
                flight_intents["flight_1_activated_time_range_A_extended"],
                flight_intents["flight_1_activated_time_range_B"],
                flight_intents["flight_2_planned_time_range_A"],
                flight_intents["flight_2_activated_time_range_A"],
                flight_intents["flight_2_activated_time_range_B"],
            )

            assert (
                self.flight_1_planned_time_range_A.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight_1_planned_time_range_A must have state Accepted"
            assert (
                self.flight_1_planned_time_range_A_extended.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight_1_planned_time_range_A_extended must have state Accepted"
            assert (
                self.flight_1_activated_time_range_A.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_1_activated_time_range_A must have state Activated"
            assert (
                self.flight_1_activated_time_range_A_extended.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_1_activated_time_range_A_extended must have state Activated"
            assert (
                self.flight_1_activated_time_range_B.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_1_activated_time_range_B must have state Activated"
            assert (
                self.flight_2_planned_time_range_A.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight_2_planned_time_range_A must have state Accepted"
            assert (
                self.flight_2_activated_time_range_A.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_2_activated_time_range_A must have state Activated"
            assert (
                self.flight_2_activated_time_range_B.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_2_activated_time_range_B must have state Activated"

            # TODO: check that the time ranges are equal where they need to be
            # TODO: check that flight data is the same across the different versions of the flight

            assert (
                self.flight_2_planned_time_range_A.request.operational_intent.priority
                > self.flight_1_planned_time_range_A.request.operational_intent.priority
            ), "flight_2 must have higher priority than flight_1"
            assert scd.vol4s_intersect(
                self.flight_1_planned_time_range_A.request.operational_intent.volumes,
                self.flight_2_planned_time_range_A.request.operational_intent.volumes,
            ), "flight_1_planned_time_range_A and flight_2_planned_time_range_A must intersect"
            assert scd.vol4s_intersect(
                self.flight_1_planned_time_range_A.request.operational_intent.volumes,
                self.flight_1_planned_time_range_A_extended.request.operational_intent.volumes,
            ), "flight_1_planned_time_range_A and flight_1_planned_time_range_A_extended must intersect"
            assert not scd.vol4s_intersect(
                self.flight_1_planned_time_range_A.request.operational_intent.volumes,
                self.flight_1_activated_time_range_B.request.operational_intent.volumes,
            ), "flight_1_planned_time_range_A and flight_1_activated_time_range_B must not intersect"

        except KeyError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: missing flight intent {e}"
            )
        except AssertionError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

    def run(self):
        self.begin_test_scenario()

        self.record_note(
            "Tested USS",
            f"{self.tested_uss.config.participant_id}",
        )
        self.record_note(
            "Control USS",
            f"{self.control_uss.config.participant_id}",
        )

        self.begin_test_case("Setup")
        if not self._setup():
            return
        self.end_test_case()

        self.begin_test_case("Attempt to plan flight in conflict")
        self._attempt_plan_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to modify planned flight in conflict")
        flight_1_op_intent_id = self._attempt_modify_planned_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to activate flight in conflict")
        self._attempt_activate_flight_conflict(flight_1_op_intent_id)
        self.end_test_case()

        self.begin_test_case("Modify activated flight with pre-existing conflict")
        flight_1_op_intent_id = self._modify_activated_flight_conflict_preexisting()
        self.end_test_case()

        self.begin_test_case("Attempt to modify activated flight in conflict")
        self._attempt_modify_activated_flight_conflict(flight_1_op_intent_id)
        self.end_test_case()

        self.end_test_scenario()

    def _setup(self) -> bool:
        if not check_capabilities(
            self,
            "Check for necessary capabilities",
            required_capabilities=[
                (
                    [self.tested_uss, self.control_uss],
                    Capability.BasicStrategicConflictDetection,
                )
            ],
            prerequisite_capabilities=[
                (self.control_uss, Capability.HighPriorityFlights)
            ],
        ):
            return False

        clear_area(
            self,
            "Area clearing",
            [
                self.flight_1_planned_time_range_A,
                self.flight_1_planned_time_range_A_extended,
                self.flight_1_activated_time_range_A,
                self.flight_1_activated_time_range_A_extended,
                self.flight_1_activated_time_range_B,
                self.flight_2_planned_time_range_A,
                self.flight_2_activated_time_range_A,
                self.flight_2_activated_time_range_B,
            ],
            [self.tested_uss, self.control_uss],
        )

        return True

    def _attempt_plan_flight_conflict(self):
        resp_flight_2, self.flight_2_id = plan_flight_intent(
            self,
            "Plan flight 2",
            self.control_uss,
            self.flight_2_planned_time_range_A.request,
        )

        with ValidateNotSharedOperationalIntent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not shared",
            self.flight_1_planned_time_range_A.request,
        ):
            _ = plan_priority_conflict_flight_intent(
                self,
                "Attempt to plan flight 1",
                self.tested_uss,
                self.flight_1_planned_time_range_A.request,
            )

        validate_shared_operational_intent(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self.flight_2_planned_time_range_A.request,
            resp_flight_2.operational_intent_id,
        )

        _ = delete_flight_intent(
            self, "Delete flight 2", self.control_uss, self.flight_2_id
        )
        self.flight_2_id = None

    def _attempt_modify_planned_flight_conflict(self) -> str:
        resp_flight_1, self.flight_1_id = plan_flight_intent(
            self,
            "Plan flight 1",
            self.tested_uss,
            self.flight_1_planned_time_range_A.request,
        )

        resp_flight_2, self.flight_2_id = plan_flight_intent(
            self,
            "Plan flight 2",
            self.control_uss,
            self.flight_2_planned_time_range_A.request,
        )

        _ = modify_planned_priority_conflict_flight_intent(
            self,
            "Attempt to modify planned flight 1 in conflict",
            self.tested_uss,
            self.flight_1_planned_time_range_A_extended.request,
            self.flight_1_id,
        )

        validate_shared_operational_intent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not modified",
            self.flight_1_planned_time_range_A.request,
            resp_flight_1.operational_intent_id,
        )
        validate_shared_operational_intent(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self.flight_2_planned_time_range_A.request,
            resp_flight_2.operational_intent_id,
        )

        return resp_flight_1.operational_intent_id

    def _attempt_activate_flight_conflict(self, flight_1_op_intent_id: str):
        _ = activate_priority_conflict_flight_intent(
            self,
            "Attempt to activate conflicting flight 1",
            self.tested_uss,
            self.flight_1_activated_time_range_A.request,
            self.flight_1_id,
        )

        validate_shared_operational_intent(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 1 not activated",
            self.flight_1_planned_time_range_A.request,
            flight_1_op_intent_id,
        )

    def _modify_activated_flight_conflict_preexisting(self) -> str:
        _ = delete_flight_intent(
            self, "Delete flight 2", self.control_uss, self.flight_2_id
        )
        self.flight_2_id = None

        _ = activate_flight_intent(
            self,
            "Activate flight 1",
            self.tested_uss,
            self.flight_1_activated_time_range_A.request,
            self.flight_1_id,
        )

        _, self.flight_2_id = plan_flight_intent(
            self,
            "Plan flight 2",
            self.control_uss,
            self.flight_2_planned_time_range_A.request,
        )

        resp_flight_2 = activate_flight_intent(
            self,
            "Activate flight 2",
            self.control_uss,
            self.flight_2_activated_time_range_A.request,
            self.flight_2_id,
        )

        resp_flight_1 = modify_activated_flight_intent(
            self,
            "Modify activated flight 1 in conflict with activated flight 2",
            self.tested_uss,
            self.flight_1_activated_time_range_A_extended.request,
            self.flight_1_id,
        )

        validate_shared_operational_intent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 sharing",
            self.flight_1_activated_time_range_A_extended.request,
            resp_flight_1.operational_intent_id,
        )
        validate_shared_operational_intent(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self.flight_2_activated_time_range_A.request,
            resp_flight_2.operational_intent_id,
        )

        return resp_flight_1.operational_intent_id

    def _attempt_modify_activated_flight_conflict(self, flight_1_op_intent_id: str):
        resp_flight_2 = modify_activated_flight_intent(
            self,
            "Modify activated flight 2 to not conflict with activated flight 1",
            self.control_uss,
            self.flight_2_activated_time_range_B.request,
            self.flight_2_id,
        )

        _ = modify_activated_priority_conflict_flight_intent(
            self,
            "Attempt to modify activated flight 1 in conflict",
            self.tested_uss,
            self.flight_1_activated_time_range_B.request,
            self.flight_1_id,
        )

        validate_shared_operational_intent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not modified",
            self.flight_1_activated_time_range_A_extended.request,
            flight_1_op_intent_id,
        )
        validate_shared_operational_intent(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self.flight_2_activated_time_range_B.request,
            resp_flight_2.operational_intent_id,
        )

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.control_uss, self.tested_uss))
        self.end_cleanup()
