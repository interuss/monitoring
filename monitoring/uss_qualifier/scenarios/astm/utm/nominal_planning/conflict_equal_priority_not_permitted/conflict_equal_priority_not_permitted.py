from typing import Optional

from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.uss_qualifier.common_data_definitions import Severity
from uas_standards.astm.f3548.v21.api import OperationalIntentState

from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    InjectFlightResult,
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
    modify_planned_conflict_flight_intent,
    modify_activated_conflict_flight_intent,
    activate_conflict_flight_intent,
    plan_conflict_flight_intent,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    ScenarioCannotContinueError,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    clear_area,
    plan_flight_intent,
    cleanup_flights,
    activate_flight_intent,
    submit_flight_intent,
)


class ConflictEqualPriorityNotPermitted(TestScenario):
    flight_1_id: Optional[str] = None
    flight_1_planned_time_range_A: FlightIntent
    flight_1_activated_time_range_A: FlightIntent
    flight_1_activated_time_range_A_extended: FlightIntent
    flight_1_planned_time_range_B: FlightIntent
    flight_1_activated_time_range_B: FlightIntent

    flight_2_id: Optional[str] = None
    flight_2_equal_prio_planned_time_range_B: FlightIntent
    flight_2_equal_prio_activated_time_range_B: FlightIntent
    flight_2_equal_prio_nonconforming_time_range_A: FlightIntent

    tested_uss: FlightPlanner
    control_uss: FlightPlanner
    dss: DSSInstance

    def __init__(
        self,
        tested_uss: FlightPlannerResource,
        control_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
        flight_intents: Optional[FlightIntentsResource] = None,
    ):
        super().__init__()
        self.tested_uss = tested_uss.flight_planner
        self.control_uss = control_uss.flight_planner
        self.dss = dss.dss

        if not flight_intents:
            msg = f"No FlightIntentsResource was provided as input to this test, it is assumed that the jurisdiction of the tested USS ({self.tested_uss.config.participant_id}) does not allow any same priority conflicts, execution of the scenario was stopped without failure"
            self.record_note(
                "Jurisdiction of tested USS does not allow any same priority conflicts",
                msg,
            )
            raise ScenarioCannotContinueError(msg)

        flight_intents = flight_intents.get_flight_intents()
        try:
            (
                self.flight_1_planned_time_range_A,
                self.flight_1_activated_time_range_A,
                self.flight_1_activated_time_range_A_extended,
                self.flight_1_planned_time_range_B,
                self.flight_1_activated_time_range_B,
                self.flight_2_equal_prio_planned_time_range_B,
                self.flight_2_equal_prio_activated_time_range_B,
                self.flight_2_equal_prio_nonconforming_time_range_A,
            ) = (
                flight_intents["flight_1_planned_time_range_A"],
                flight_intents["flight_1_activated_time_range_A"],
                flight_intents["flight_1_activated_time_range_A_extended"],
                flight_intents["flight_1_planned_time_range_B"],
                flight_intents["flight_1_activated_time_range_B"],
                flight_intents["flight_2_equal_prio_planned_time_range_B"],
                flight_intents["flight_2_equal_prio_activated_time_range_B"],
                flight_intents["flight_2_equal_prio_nonconforming_time_range_A"],
            )

            assert (
                self.flight_1_planned_time_range_A.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight_1_planned_time_range_A must have state Accepted"
            assert (
                self.flight_1_activated_time_range_A.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_1_activated_time_range_A must have state Activated"
            assert (
                self.flight_1_activated_time_range_A_extended.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_1_activated_time_range_A_extended must have state Activated"
            assert (
                self.flight_1_planned_time_range_B.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight_1_planned_time_range_B must have state Accepted"
            assert (
                self.flight_1_activated_time_range_B.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_1_activated_time_range_B must have state Activated"
            assert (
                self.flight_2_equal_prio_planned_time_range_B.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight_2_equal_prio_planned_time_range_B must have state Accepted"
            assert (
                self.flight_2_equal_prio_activated_time_range_B.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "flight_2_equal_prio_activated_time_range_B must have state Activated"
            assert (
                self.flight_2_equal_prio_nonconforming_time_range_A.request.operational_intent.state
                == OperationalIntentState.Nonconforming
            ), "flight_2_equal_prio_nonconforming_time_range_A must have state Nonconforming"

            assert (
                self.flight_2_equal_prio_planned_time_range_B.request.operational_intent.priority
                == self.flight_1_planned_time_range_A.request.operational_intent.priority
            ), "flight_2 must have priority equal to flight_1"
            assert not Volume4DCollection.from_f3548v21(
                self.flight_1_planned_time_range_A.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_f3548v21(
                    self.flight_2_equal_prio_planned_time_range_B.request.operational_intent.volumes
                )
            ), "flight_1_planned_time_range_A and flight_2_equal_prio_planned_time_range_B must not intersect"
            assert not Volume4DCollection.from_f3548v21(
                self.flight_1_planned_time_range_A.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_f3548v21(
                    self.flight_1_activated_time_range_B.request.operational_intent.volumes
                )
            ), "flight_1_planned_time_range_A and flight_1_activated_time_range_B must not intersect"
            assert Volume4DCollection.from_f3548v21(
                self.flight_1_activated_time_range_B.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_f3548v21(
                    self.flight_2_equal_prio_activated_time_range_B.request.operational_intent.volumes
                )
            ), "flight_1_activated_time_range_B and flight_2_equal_prio_activated_time_range_B must intersect"
            assert Volume4DCollection.from_f3548v21(
                self.flight_1_activated_time_range_A.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_f3548v21(
                    self.flight_2_equal_prio_nonconforming_time_range_A.request.operational_intent.off_nominal_volumes
                )
            ), "flight_1_activated_time_range_A.volumes and flight_2_equal_prio_nonconforming_time_range_A.off_nominal_volumes must intersect"

            assert (
                len(
                    self.flight_2_equal_prio_nonconforming_time_range_A.request.operational_intent.off_nominal_volumes
                )
                > 0
            ), "flight_2_equal_prio_nonconforming_time_range_A must have off-nominal volume"

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

        self.begin_test_case("Attempt to activate flight in conflict")
        self._attempt_activate_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to modify planned flight in conflict")
        self._attempt_modify_planned_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to modify activated flight in conflict")
        flight_1_op_intent_id = self._attempt_modify_activated_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Modify activated flight with pre-existing conflict")
        self._modify_activated_flight_preexisting_conflict(flight_1_op_intent_id)
        self.end_test_case()

        self.end_test_scenario()

    def _setup(self) -> bool:
        self.begin_test_step("Check for flight planning readiness")

        for uss in (self.tested_uss, self.control_uss):
            error, query = uss.get_readiness()
            self.record_query(query)
            with self.check(
                "Flight planning USS not ready", [uss.participant_id]
            ) as check:
                if error:
                    check.record_failed(
                        "Error determining readiness",
                        Severity.High,
                        "Error: " + error,
                        query_timestamps=[query.request.timestamp],
                    )

        self.end_test_step()

        clear_area(
            self,
            "Area clearing",
            [
                self.flight_1_planned_time_range_A,
                self.flight_1_activated_time_range_A,
                self.flight_1_activated_time_range_A_extended,
                self.flight_1_planned_time_range_B,
                self.flight_1_activated_time_range_B,
                self.flight_2_equal_prio_planned_time_range_B,
                self.flight_2_equal_prio_activated_time_range_B,
                self.flight_2_equal_prio_nonconforming_time_range_A,
            ],
            [self.tested_uss, self.control_uss],
        )

        return True

    def _attempt_plan_flight_conflict(self):
        _, self.flight_2_id = plan_flight_intent(
            self,
            "Plan flight 2",
            self.control_uss,
            self.flight_2_equal_prio_planned_time_range_B.request,
        )

        resp_flight_2 = activate_flight_intent(
            self,
            "Activate flight 2",
            self.control_uss,
            self.flight_2_equal_prio_activated_time_range_B.request,
            self.flight_2_id,
        )

        validate_shared_operational_intent(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self.flight_2_equal_prio_activated_time_range_B.request,
            resp_flight_2.operational_intent_id,
        )

        with ValidateNotSharedOperationalIntent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not shared",
            self.flight_1_planned_time_range_B.request,
        ):
            _ = plan_conflict_flight_intent(
                self,
                "Attempt to plan flight 1",
                self.tested_uss,
                self.flight_1_planned_time_range_B.request,
            )

    def _attempt_activate_flight_conflict(self):
        with ValidateNotSharedOperationalIntent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not shared",
            self.flight_1_activated_time_range_B.request,
        ):
            _ = activate_conflict_flight_intent(
                self,
                "Attempt to directly activate conflicting flight 1",
                self.tested_uss,
                self.flight_1_activated_time_range_B.request,
                self.flight_1_id,
            )

    def _attempt_modify_planned_flight_conflict(self):
        resp_flight_1, self.flight_1_id = plan_flight_intent(
            self,
            "Plan flight 1",
            self.tested_uss,
            self.flight_1_planned_time_range_A.request,
        )
        validate_shared_operational_intent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 sharing",
            self.flight_1_planned_time_range_A.request,
            resp_flight_1.operational_intent_id,
        )

        _ = modify_planned_conflict_flight_intent(
            self,
            "Attempt to modify planned flight 1 in conflict",
            self.tested_uss,
            self.flight_1_planned_time_range_B.request,
            self.flight_1_id,
        )

        validate_shared_operational_intent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 not modified",
            self.flight_1_planned_time_range_A.request,
            resp_flight_1.operational_intent_id,
            skip_if_not_found=True,
        )

    def _attempt_modify_activated_flight_conflict(self) -> str:
        resp_flight_1 = activate_flight_intent(
            self,
            "Activate flight 1",
            self.tested_uss,
            self.flight_1_activated_time_range_A.request,
            self.flight_1_id,
        )
        validate_shared_operational_intent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 sharing",
            self.flight_1_activated_time_range_A.request,
            resp_flight_1.operational_intent_id,
        )

        _ = modify_activated_conflict_flight_intent(
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
            self.flight_1_activated_time_range_A.request,
            resp_flight_1.operational_intent_id,
            skip_if_not_found=True,
        )

        return resp_flight_1.operational_intent_id

    def _modify_activated_flight_preexisting_conflict(
        self, orig_flight_1_op_intent_id: str
    ):
        resp_flight_1 = activate_flight_intent(
            self,
            "Activate flight 1",
            self.tested_uss,
            self.flight_1_activated_time_range_A.request,
            self.flight_1_id,
        )
        validate_shared_operational_intent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight 1 sharing",
            self.flight_1_activated_time_range_A.request,
            resp_flight_1.operational_intent_id,
        )

        # TODO: the following call requires the control USS to support CMSA role,
        #  but as there is currently no explicit way of knowing if it is the case
        #  or not, we assume that a Rejected result means the USS does not
        #  support the CMSA role, in which case we interrupt the scenario.
        resp_flight_2, _ = submit_flight_intent(
            self,
            "Declare flight 2 non-conforming",
            "Successful transition to non-conforming state",
            {InjectFlightResult.Planned, InjectFlightResult.Rejected},
            {InjectFlightResult.Failed: "Failure"},
            self.control_uss,
            self.flight_2_equal_prio_nonconforming_time_range_A.request,
            self.flight_2_id,
        )
        if resp_flight_2.result == InjectFlightResult.Rejected:
            msg = f"{self.control_uss.config.participant_id} rejected transition to a Nonconforming state because it does not support CMSA role, execution of the scenario was stopped without failure"
            self.record_note("Control USS does not support CMSA role", msg)
            raise ScenarioCannotContinueError(msg)

        validate_shared_operational_intent(
            self,
            self.control_uss,
            self.dss,
            "Validate flight 2 sharing",
            self.flight_2_equal_prio_nonconforming_time_range_A.request,
            resp_flight_2.operational_intent_id,
        )

        resp_flight_1, _ = submit_flight_intent(
            self,
            "Attempt to modify activated flight 1 in conflict with activated flight 2",
            "Successful modification or rejection",
            {InjectFlightResult.ReadyToFly, InjectFlightResult.Rejected},
            {InjectFlightResult.Failed: "Failure"},
            self.tested_uss,
            self.flight_1_activated_time_range_A_extended.request,
            self.flight_1_id,
        )

        if resp_flight_1.result == InjectFlightResult.ReadyToFly:
            validate_shared_operational_intent(
                self,
                self.tested_uss,
                self.dss,
                "Validate flight 1",
                self.flight_1_activated_time_range_A_extended.request,
                resp_flight_1.operational_intent_id,
            )
        elif resp_flight_1.result == InjectFlightResult.Rejected:
            validate_shared_operational_intent(
                self,
                self.tested_uss,
                self.dss,
                "Validate flight 1",
                self.flight_1_activated_time_range_A.request,
                orig_flight_1_op_intent_id,
                skip_if_not_found=True,
            )

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.control_uss, self.tested_uss))
        self.end_cleanup()
