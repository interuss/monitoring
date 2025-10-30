import arrow
from uas_standards.astm.f3548.v21.api import OperationalIntentReference
from uas_standards.astm.f3548.v21.constants import (
    Scope,
)

from monitoring.monitorlib.clients.flight_planning.client import (
    FlightPlannerClient,
)
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
from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import FlightIntentsResource
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerResource,
)
from monitoring.uss_qualifier.scenarios.astm.utm.clear_area_validation import (
    validate_clear_area,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import OpIntentValidator
from monitoring.uss_qualifier.scenarios.flight_planning.prioritization_test_steps import (
    activate_conflict_flight,
    modify_activated_conflict_flight,
    modify_planned_conflict_flight,
    plan_conflict_flight,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    activate_flight,
    cleanup_flights,
    delete_flight,
    plan_flight,
    submit_flight,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    ScenarioCannotContinueError,
    TestScenario,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class ConflictEqualPriorityNotPermitted(TestScenario):
    times: dict[TimeDuringTest, Time]

    flight1_id: str | None = None
    flight1_planned: FlightInfoTemplate
    flight1_activated: FlightInfoTemplate
    flight1m_activated: FlightInfoTemplate
    flight1c_planned: FlightInfoTemplate
    flight1c_activated: FlightInfoTemplate

    flight2_id: str | None = None
    flight2m_planned: FlightInfoTemplate
    flight2_planned: FlightInfoTemplate
    flight2_activated: FlightInfoTemplate
    flight2_nonconforming: FlightInfoTemplate

    tested_uss: FlightPlannerClient
    control_uss: FlightPlannerClient
    dss: DSSInstance

    def __init__(
        self,
        tested_uss: FlightPlannerResource,
        control_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
        flight_intents: FlightIntentsResource | None = None,
    ):
        super().__init__()
        self.tested_uss = tested_uss.client
        self.control_uss = control_uss.client

        scopes = {
            Scope.StrategicCoordination: "search for operational intent references to verify outcomes of planning activities and retrieve operational intent details"
        }
        if dss.can_use_scope(Scope.ConformanceMonitoringForSituationalAwareness):
            scopes[Scope.ConformanceMonitoringForSituationalAwareness] = (
                "query for telemetry for off-nominal operational intents"
            )

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
            f"{self.tested_uss.participant_id}",
        )
        self.record_note(
            "Control USS",
            f"{self.control_uss.participant_id}",
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
                self.control_uss,
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
                self.control_uss,
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
                self.tested_uss,
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
                self.tested_uss,
                flight1_activated,
                self.flight1_id,
            )
            validator.expect_not_shared()
        self.end_test_step()

    def _attempt_modify_planned_flight_conflict(
        self,
    ) -> OperationalIntentReference | None:
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
                self.tested_uss,
                flight1c_planned,
                nearby_potential_conflict=True,
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
                self.tested_uss,
                flight1_planned,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                flight1c_planned, skip_if_not_found=True
            )
        self.end_test_step()

        return flight_1_oi_ref

    def _attempt_modify_activated_flight_conflict(
        self, flight_1_oi_ref: OperationalIntentReference | None
    ) -> OperationalIntentReference | None:
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
                self.tested_uss,
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
            modify_resp = modify_activated_conflict_flight(
                self,
                self.tested_uss,
                flight1_activated,
                self.flight1_id,
            )
            validator.expect_not_shared()
        self.end_test_step()

        if modify_resp.activity_result == PlanningActivityResult.NotSupported:
            self.begin_test_step(
                "Delete Flight 1c if USS did not support its modification"
            )
            if self.flight1_id is None:
                raise ValueError("flight1_id is None")
            delete_flight(self, self.tested_uss, self.flight1_id)
            self.flight1_id = None
            self.end_test_step()

        self.begin_test_step("Delete Flight 2")
        delete_flight(self, self.control_uss, self.flight2_id)
        self.flight2_id = None
        self.end_test_step()

        return flight_1_oi_ref

    def _modify_activated_flight_preexisting_conflict(
        self,
        flight_1_oi_ref: OperationalIntentReference | None,
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
            _, self.flight1_id = activate_flight(
                self,
                self.tested_uss,
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
                self.control_uss,
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
                flight_planner=self.control_uss,
                flight_info=flight2_nonconforming,
                flight_id=self.flight2_id,
            )

            if resp_flight_2.activity_result == PlanningActivityResult.NotSupported:
                msg = f"{self.control_uss.participant_id} does not support the transition to a Nonconforming state; execution of the scenario was stopped without failure"
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
                success_check="Successful flight intent handling",
                expected_results={
                    (PlanningActivityResult.Completed, FlightPlanStatus.OkToFly),
                    (PlanningActivityResult.Rejected, FlightPlanStatus.OkToFly),
                    (PlanningActivityResult.NotSupported, FlightPlanStatus.OkToFly),
                },
                failed_checks={PlanningActivityResult.Failed: "Failure"},
                flight_planner=self.tested_uss,
                flight_info=flight1m_activated,
                flight_id=self.flight1_id,
            )

            if resp_flight_1.activity_result == PlanningActivityResult.Completed:
                validator.expect_shared(flight1m_activated)
            elif resp_flight_1.activity_result in {
                PlanningActivityResult.Rejected,
                PlanningActivityResult.NotSupported,
            }:
                validator.expect_not_shared()
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.control_uss, self.tested_uss))
        self.end_cleanup()
