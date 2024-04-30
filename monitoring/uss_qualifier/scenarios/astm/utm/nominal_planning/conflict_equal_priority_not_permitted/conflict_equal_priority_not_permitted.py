from typing import Optional, Dict

import arrow

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
    FlightInfo,
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
    validate_flight_intent_templates,
    ExpectedFlightIntent,
)
from monitoring.uss_qualifier.scenarios.astm.utm.clear_area_validation import (
    validate_clear_area,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentReference,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlanner,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerResource,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    OpIntentValidator,
)
from monitoring.uss_qualifier.scenarios.flight_planning.prioritization_test_steps import (
    plan_conflict_flight,
    activate_conflict_flight,
    modify_planned_conflict_flight,
    modify_activated_conflict_flight,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    ScenarioCannotContinueError,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    plan_flight,
    activate_flight,
    delete_flight,
    submit_flight,
    cleanup_flights_fp_client,
)


class ConflictEqualPriorityNotPermitted(TestScenario):

    times: Dict[TimeDuringTest, Time]

    flight1_id: Optional[str] = None
    flight1_planned: FlightInfoTemplate
    flight1_activated: FlightInfoTemplate
    flight1m_activated: FlightInfoTemplate
    flight1c_planned: FlightInfoTemplate
    flight1c_activated: FlightInfoTemplate

    flight2_id: Optional[str] = None
    flight2m_planned: FlightInfoTemplate
    flight2_planned: FlightInfoTemplate
    flight2_activated: FlightInfoTemplate
    flight2_nonconforming: FlightInfoTemplate

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

        scopes = {
            Scope.StrategicCoordination: "search for operational intent references to verify outcomes of planning activities and retrieve operational intent details"
        }
        if dss.can_use_scope(Scope.ConformanceMonitoringForSituationalAwareness):
            scopes[
                Scope.ConformanceMonitoringForSituationalAwareness
            ] = "query for telemetry for off-nominal operational intents"

        self.dss = dss.get_instance(scopes)

        expected_flight_intents = [
            ExpectedFlightIntent(
                "flight1_planned",
                "Flight 1",
                must_conflict_with=["Flight 2"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight1_activated",
                "Flight 1",
                must_conflict_with=["Flight 2"],
                usage_state=AirspaceUsageState.InUse,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight1m_activated",
                "Flight 1m",
                must_conflict_with=["Flight 2"],
                usage_state=AirspaceUsageState.InUse,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight1c_planned",
                "Flight 1c",
                must_not_conflict_with=["Flight 2"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight1c_activated",
                "Flight 1c",
                must_not_conflict_with=["Flight 2"],
                usage_state=AirspaceUsageState.InUse,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "equal_prio_flight2m_planned",
                "Flight 2m",
                must_not_conflict_with=["Flight 1"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "equal_prio_flight2_planned",
                "Flight 2",
                must_conflict_with=["Flight 1", "Flight 1m"],
                must_not_conflict_with=["Flight 1c"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "equal_prio_flight2_activated",
                "Flight 2",
                must_conflict_with=["Flight 1", "Flight 1m"],
                must_not_conflict_with=["Flight 1c"],
                usage_state=AirspaceUsageState.InUse,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "equal_prio_flight2_nonconforming",
                "Flight 2",
                must_conflict_with=["Flight 1", "Flight 1m"],
                must_not_conflict_with=["Flight 1c"],
                usage_state=AirspaceUsageState.InUse,
            ),  # Note: this intent expected to produce Nonconforming state, but this is hard to verify without telemetry.  UAS state is not actually off-nominal.
        ]

        templates = flight_intents.get_flight_intents()
        try:
            self._intents_extent = validate_flight_intent_templates(
                templates, expected_flight_intents
            )
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

        for efi in expected_flight_intents:
            setattr(
                self, efi.intent_id.replace("equal_prio_", ""), templates[efi.intent_id]
            )

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
            f"{self.tested_uss.config.participant_id}",
        )
        self.record_note(
            "Control USS",
            f"{self.control_uss.config.participant_id}",
        )

        self.begin_test_case("Prerequisites check")
        self.begin_test_step("Verify area is clear")
        validate_clear_area(
            self,
            self.dss,
            [self._intents_extent],
            ignore_self=True,
        )
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Attempt to plan flight into conflict")
        self._attempt_plan_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to activate flight into conflict")
        self._attempt_activate_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to modify planned flight into conflict")
        flight_1_oi_ref = self._attempt_modify_planned_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to modify activated flight into conflict")
        flight_1_oi_ref = self._attempt_modify_activated_flight_conflict(
            flight_1_oi_ref
        )
        self.end_test_case()

        self.begin_test_case("Modify activated flight with pre-existing conflict")
        self._modify_activated_flight_preexisting_conflict(flight_1_oi_ref)
        self.end_test_case()

        self.end_test_scenario()

    def _attempt_plan_flight_conflict(self):
        self.begin_test_step("Plan Flight 2")
        flight2_planned = self.resolve_flight(self.flight2_planned)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            flight2_planned,
        ) as validator:
            _, self.flight2_id = plan_flight(
                self,
                self.control_uss.client,
                flight2_planned,
            )
            flight_2_oi_ref = validator.expect_shared(flight2_planned)
        self.end_test_step()

        self.begin_test_step("Activate Flight 2")
        flight2_activated = self.resolve_flight(self.flight2_activated)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            flight2_activated,
            flight_2_oi_ref,
        ) as validator:
            activate_flight(
                self,
                self.control_uss.client,
                flight2_activated,
                self.flight2_id,
            )
            validator.expect_shared(flight2_activated)
        self.end_test_step()

        self.begin_test_step("Attempt to plan Flight 1")
        flight1_planned = self.resolve_flight(self.flight1_planned)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            flight1_planned,
        ) as validator:
            plan_conflict_flight(
                self,
                self.tested_uss.client,
                flight1_planned,
            )
            validator.expect_not_shared()
        self.end_test_step()

    def _attempt_activate_flight_conflict(self):
        self.begin_test_step("Attempt to directly activate conflicting Flight 1")
        flight1_activated = self.resolve_flight(self.flight1_activated)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            flight1_activated,
        ) as validator:
            activate_conflict_flight(
                self,
                self.tested_uss.client,
                flight1_activated,
                self.flight1_id,
            )
            validator.expect_not_shared()
        self.end_test_step()

    def _attempt_modify_planned_flight_conflict(
        self,
    ) -> Optional[OperationalIntentReference]:
        self.begin_test_step("Plan Flight 1c")
        flight1c_planned = self.resolve_flight(self.flight1c_planned)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            flight1c_planned,
        ) as validator:
            _, self.flight1_id = plan_flight(
                self,
                self.tested_uss.client,
                flight1c_planned,
            )
            flight_1_oi_ref = validator.expect_shared(flight1c_planned)
        self.end_test_step()

        self.begin_test_step("Attempt to modify planned Flight 1c into conflict")
        flight1_planned = self.resolve_flight(self.flight1_planned)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            [flight1c_planned, flight1_planned],
            flight_1_oi_ref,
        ) as validator:
            modify_planned_conflict_flight(
                self,
                self.tested_uss.client,
                flight1_planned,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                flight1c_planned, skip_if_not_found=True
            )
        self.end_test_step()

        return flight_1_oi_ref

    def _attempt_modify_activated_flight_conflict(
        self, flight_1_oi_ref: Optional[OperationalIntentReference]
    ) -> Optional[OperationalIntentReference]:
        self.begin_test_step("Activate Flight 1c")
        flight1c_activated = self.resolve_flight(self.flight1c_activated)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            flight1c_activated,
            flight_1_oi_ref,
        ) as validator:
            activate_flight(
                self,
                self.tested_uss.client,
                flight1c_activated,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(flight1c_activated)
        self.end_test_step()

        self.begin_test_step("Attempt to modify activated Flight 1c into conflict")
        flight1_activated = self.resolve_flight(self.flight1_activated)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            [flight1c_activated, flight1_activated],
            flight_1_oi_ref,
        ) as validator:
            modify_activated_conflict_flight(
                self,
                self.tested_uss.client,
                flight1_activated,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                flight1c_activated, skip_if_not_found=True
            )
        self.end_test_step()

        self.begin_test_step("Delete Flight 2")
        delete_flight(self, self.control_uss.client, self.flight2_id)
        self.flight2_id = None
        self.end_test_step()

        return flight_1_oi_ref

    def _modify_activated_flight_preexisting_conflict(
        self,
        flight_1_oi_ref: Optional[OperationalIntentReference],
    ):
        self.begin_test_step("Activate Flight 1")
        flight1_activated = self.resolve_flight(self.flight1_activated)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            flight1_activated,
            flight_1_oi_ref,
        ) as validator:
            activate_flight(
                self,
                self.tested_uss.client,
                flight1_activated,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(flight1_activated)
        self.end_test_step()

        self.begin_test_step("Plan Flight 2m")
        flight2m_planned = self.resolve_flight(self.flight2m_planned)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            flight2m_planned,
        ) as validator:
            _, self.flight2_id = plan_flight(
                self,
                self.control_uss.client,
                flight2m_planned,
            )
            flight_2_oi_ref = validator.expect_shared(flight2m_planned)
        self.end_test_step()

        self.begin_test_step("Declare Flight 2 non-conforming")
        flight2_nonconforming = self.resolve_flight(self.flight2_nonconforming)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            [flight2m_planned, flight2_nonconforming],
            flight_2_oi_ref,
        ) as validator:
            resp_flight_2, _ = submit_flight(
                scenario=self,
                success_check="Successful transition to non-conforming state",
                expected_results={
                    (PlanningActivityResult.Completed, FlightPlanStatus.OffNominal),
                    (PlanningActivityResult.NotSupported, FlightPlanStatus.Planned),
                },
                failed_checks={PlanningActivityResult.Failed: "Failure"},
                flight_planner=self.control_uss.client,
                flight_info=flight2_nonconforming,
                flight_id=self.flight2_id,
            )

            if resp_flight_2.activity_result == PlanningActivityResult.NotSupported:
                msg = f"{self.control_uss.config.participant_id} does not support the transition to a Nonconforming state; execution of the scenario was stopped without failure"
                self.record_note("Control USS does not support CMSA role", msg)
                raise ScenarioCannotContinueError(msg)

            validator.expect_shared(flight2_nonconforming)
        self.end_test_step()

        self.begin_test_step(
            "Attempt to modify activated Flight 1 in conflict with nonconforming Flight 2"
        )
        flight1m_activated = self.resolve_flight(self.flight1m_activated)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            [flight1_activated, flight1m_activated],
            flight_1_oi_ref,
        ) as validator:
            resp_flight_1, _ = submit_flight(
                scenario=self,
                success_check="Successful modification or rejection",
                expected_results={
                    (PlanningActivityResult.Completed, FlightPlanStatus.OkToFly),
                    (PlanningActivityResult.Rejected, FlightPlanStatus.OkToFly),
                    (PlanningActivityResult.Rejected, FlightPlanStatus.Closed),
                },
                failed_checks={PlanningActivityResult.Failed: "Failure"},
                flight_planner=self.tested_uss.client,
                flight_info=flight1m_activated,
                flight_id=self.flight1_id,
            )

            if resp_flight_1.activity_result == PlanningActivityResult.Completed:
                validator.expect_shared(flight1m_activated)
            elif resp_flight_1.activity_result == PlanningActivityResult.Rejected:
                validator.expect_shared(flight1_activated, skip_if_not_found=True)
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights_fp_client(
            self, (self.control_uss.client, self.tested_uss.client)
        )
        self.end_cleanup()
