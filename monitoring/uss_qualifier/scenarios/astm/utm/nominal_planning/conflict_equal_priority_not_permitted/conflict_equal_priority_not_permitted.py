from typing import Optional

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
)
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
from monitoring.monitorlib.geotemporal import Volume4DCollection, Volume4D

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
    OpIntentValidator,
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
    plan_flight_intent,
    cleanup_flights,
    activate_flight_intent,
    submit_flight_intent,
    delete_flight_intent,
)
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightResponseResult,
)


class ConflictEqualPriorityNotPermitted(TestScenario):
    flight1_id: Optional[str] = None
    flight1_planned: FlightIntent
    flight1_activated: FlightIntent
    flight1m_activated: FlightIntent
    flight1c_planned: FlightIntent
    flight1c_activated: FlightIntent

    flight2_id: Optional[str] = None
    flight2m_planned: FlightIntent
    flight2_planned: FlightIntent
    flight2_activated: FlightIntent
    flight2_nonconforming: FlightIntent

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
            validate_flight_intent_templates(templates, expected_flight_intents)
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

        extents = []
        for efi in expected_flight_intents:
            intent = FlightIntent.from_flight_info_template(templates[efi.intent_id])
            extents.extend(intent.request.operational_intent.volumes)
            extents.extend(intent.request.operational_intent.off_nominal_volumes)
            setattr(self, efi.intent_id.replace("equal_prio_", ""), intent)

        self._intents_extent = Volume4DCollection.from_interuss_scd_api(
            extents
        ).bounding_volume.to_f3548v21()

    def run(self, context: ExecutionContext):
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
            [Volume4D.from_f3548v21(self._intents_extent)],
            ignore_self=True,
        )
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Attempt to plan flight into conflict")
        _ = self._attempt_plan_flight_conflict()
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

    def _attempt_plan_flight_conflict(self) -> OperationalIntentReference:
        self.begin_test_step("Plan Flight 2")
        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            self._intents_extent,
        ) as validator:
            _, self.flight2_id, _ = plan_flight_intent(
                self,
                self.control_uss,
                self.flight2_planned.request,
            )
            flight_2_oi_ref = validator.expect_shared(self.flight2_planned.request)
        self.end_test_step()

        self.begin_test_step("Activate Flight 2")
        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            self._intents_extent,
            flight_2_oi_ref,
        ) as validator:
            activate_flight_intent(
                self,
                self.control_uss,
                self.flight2_activated.request,
                self.flight2_id,
            )
            flight_2_oi_ref = validator.expect_shared(self.flight2_activated.request)
        self.end_test_step()

        self.begin_test_step("Attempt to plan Flight 1")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            self._intents_extent,
        ) as validator:
            plan_conflict_flight_intent(
                self,
                self.tested_uss,
                self.flight1_planned.request,
            )
            validator.expect_not_shared()
        self.end_test_step()

        return flight_2_oi_ref

    def _attempt_activate_flight_conflict(self):
        self.begin_test_step("Attempt to directly activate conflicting Flight 1")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            self._intents_extent,
        ) as validator:
            activate_conflict_flight_intent(
                self,
                self.tested_uss,
                self.flight1_activated.request,
                self.flight1_id,
            )
            validator.expect_not_shared()
        self.end_test_step()

    def _attempt_modify_planned_flight_conflict(
        self,
    ) -> Optional[OperationalIntentReference]:
        self.begin_test_step("Plan Flight 1c")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            self._intents_extent,
        ) as validator:
            _, self.flight1_id, _ = plan_flight_intent(
                self,
                self.tested_uss,
                self.flight1c_planned.request,
            )
            flight_1_oi_ref = validator.expect_shared(self.flight1c_planned.request)
        self.end_test_step()

        self.begin_test_step("Attempt to modify planned Flight 1c into conflict")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            modify_planned_conflict_flight_intent(
                self,
                self.tested_uss,
                self.flight1_planned.request,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                self.flight1c_planned.request, skip_if_not_found=True
            )
        self.end_test_step()

        return flight_1_oi_ref

    def _attempt_modify_activated_flight_conflict(
        self, flight_1_oi_ref: Optional[OperationalIntentReference]
    ) -> Optional[OperationalIntentReference]:
        self.begin_test_step("Activate Flight 1c")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            activate_flight_intent(
                self,
                self.tested_uss,
                self.flight1c_activated.request,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(self.flight1c_activated.request)
        self.end_test_step()

        self.begin_test_step("Attempt to modify activated Flight 1c into conflict")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            modify_activated_conflict_flight_intent(
                self,
                self.tested_uss,
                self.flight1_activated.request,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                self.flight1c_activated.request, skip_if_not_found=True
            )
        self.end_test_step()

        self.begin_test_step("Delete Flight 2")
        _ = delete_flight_intent(self, self.control_uss, self.flight2_id)
        self.flight2_id = None
        self.end_test_step()

        return flight_1_oi_ref

    def _modify_activated_flight_preexisting_conflict(
        self,
        flight_1_oi_ref: Optional[OperationalIntentReference],
    ):
        self.begin_test_step("Activate Flight 1")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            activate_flight_intent(
                self,
                self.tested_uss,
                self.flight1_activated.request,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(self.flight1_activated.request)
        self.end_test_step()

        self.begin_test_step("Plan Flight 2m")
        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            self._intents_extent,
        ) as validator:
            _, self.flight2_id, _ = plan_flight_intent(
                self,
                self.control_uss,
                self.flight2m_planned.request,
            )
            flight_2_oi_ref = validator.expect_shared(self.flight2m_planned.request)
        self.end_test_step()

        self.begin_test_step("Declare Flight 2 non-conforming")
        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            self._intents_extent,
            flight_2_oi_ref,
        ) as validator:
            resp_flight_2, _, _ = submit_flight_intent(
                self,
                "Successful transition to non-conforming state",
                {
                    InjectFlightResponseResult.ReadyToFly,
                    InjectFlightResponseResult.NotSupported,
                },
                {InjectFlightResponseResult.Failed: "Failure"},
                self.control_uss,
                self.flight2_nonconforming.request,
                self.flight2_id,
            )

            if resp_flight_2.result == InjectFlightResponseResult.NotSupported:
                msg = f"{self.control_uss.config.participant_id} does not support the transition to a Nonconforming state; execution of the scenario was stopped without failure"
                self.record_note("Control USS does not support CMSA role", msg)
                raise ScenarioCannotContinueError(msg)

            validator.expect_shared(self.flight2_nonconforming.request)
        self.end_test_step()

        self.begin_test_step(
            "Attempt to modify activated Flight 1 in conflict with nonconforming Flight 2"
        )
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            resp_flight_1, _, _ = submit_flight_intent(
                self,
                "Successful modification or rejection",
                {
                    InjectFlightResponseResult.ReadyToFly,
                    InjectFlightResponseResult.Rejected,
                },
                {InjectFlightResponseResult.Failed: "Failure"},
                self.tested_uss,
                self.flight1m_activated.request,
                self.flight1_id,
            )

            if resp_flight_1.result == InjectFlightResponseResult.ReadyToFly:
                validator.expect_shared(self.flight1m_activated.request)
            elif resp_flight_1.result == InjectFlightResponseResult.Rejected:
                validator.expect_shared(
                    self.flight1_activated.request, skip_if_not_found=True
                )
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.control_uss, self.tested_uss))
        self.end_cleanup()
