from typing import Optional, Tuple

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentReference,
)

from monitoring.monitorlib.geotemporal import Volume4DCollection, Volume4D
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightResponseResult,
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
    OpIntentValidator,
)
from monitoring.uss_qualifier.scenarios.flight_planning.prioritization_test_steps import (
    activate_priority_conflict_flight_intent,
    plan_priority_conflict_flight_intent,
    modify_planned_priority_conflict_flight_intent,
    modify_activated_priority_conflict_flight_intent,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    plan_flight_intent,
    cleanup_flights,
    activate_flight_intent,
    delete_flight_intent,
    modify_activated_flight_intent,
)


class ConflictHigherPriority(TestScenario):
    flight1_id: Optional[str] = None
    flight1_planned: FlightIntent
    flight1m_planned: FlightIntent
    flight1_activated: FlightIntent
    flight1m_activated: FlightIntent
    flight1c_activated: FlightIntent

    flight2_id: Optional[str] = None
    flight2_planned: FlightIntent
    flight2_activated: FlightIntent
    flight2m_activated: FlightIntent

    tested_uss: FlightPlanner
    control_uss: FlightPlanner
    dss: DSSInstance

    _intents_extent: Volume4D

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

        expected_flight_intents = [
            ExpectedFlightIntent(
                "flight1_planned",
                "Flight 1",
                must_conflict_with=["Flight 2"],
                must_not_conflict_with=["Flight 2m"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight1_activated",
                "Flight 1",
                must_conflict_with=["Flight 2"],
                must_not_conflict_with=["Flight 2m"],
                usage_state=AirspaceUsageState.InUse,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight1m_planned",
                "Flight 1m",
                must_conflict_with=["Flight 2"],
                usage_state=AirspaceUsageState.Planned,
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
                "flight1c_activated",
                "Flight 1c",
                must_conflict_with=["Flight 2m"],
                usage_state=AirspaceUsageState.InUse,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight2_planned",
                "Flight 2",
                must_conflict_with=["Flight 1"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
                f3548v21_priority_higher_than=["Flight 1"],
            ),
            ExpectedFlightIntent(
                "flight2_activated",
                name="Flight 2",
                must_conflict_with=["Flight 1"],
                usage_state=AirspaceUsageState.InUse,
                uas_state=UasState.Nominal,
                f3548v21_priority_higher_than=["Flight 1"],
            ),
            ExpectedFlightIntent(
                "flight2m_activated",
                name="Flight 2m",
                must_conflict_with=["Flight 1c"],
                must_not_conflict_with=["Flight 1"],
                usage_state=AirspaceUsageState.InUse,
                uas_state=UasState.Nominal,
                f3548v21_priority_higher_than=["Flight 1"],
            ),
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
            setattr(self, efi.intent_id, intent)

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

        self.begin_test_case("Attempt to plan flight in conflict")
        self._attempt_plan_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to modify planned flight in conflict")
        flight_1_oi_ref = self._attempt_modify_planned_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to activate flight in conflict")
        flight_1_oi_ref = self._attempt_activate_flight_conflict(flight_1_oi_ref)
        self.end_test_case()

        self.begin_test_case("Modify activated flight with pre-existing conflict")
        (
            flight_1_intent,
            flight_1_oi_ref,
            flight_2_oi_ref,
        ) = self._modify_activated_flight_conflict_preexisting(flight_1_oi_ref)
        self.end_test_case()

        self.begin_test_case("Attempt to modify activated flight in conflict")
        self._attempt_modify_activated_flight_conflict(
            flight_1_intent, flight_1_oi_ref, flight_2_oi_ref
        )
        self.end_test_case()

        self.end_test_scenario()

    def _attempt_plan_flight_conflict(self):
        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate Flight 2 sharing",
            self._intents_extent,
        ) as validator:
            self.begin_test_step("Plan Flight 2")
            resp_flight_2, self.flight2_id, _ = plan_flight_intent(
                self,
                self.control_uss,
                self.flight2_planned.request,
            )
            self.end_test_step()
            validator.expect_shared(self.flight2_planned.request)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate Flight 1 not shared",
            self._intents_extent,
        ) as validator:
            self.begin_test_step("Attempt to plan Flight 1")
            _ = plan_priority_conflict_flight_intent(
                self,
                self.tested_uss,
                self.flight1_planned.request,
            )
            self.end_test_step()
            validator.expect_not_shared()

        _ = delete_flight_intent(
            self, "Delete Flight 2", self.control_uss, self.flight2_id
        )
        self.flight2_id = None

    def _attempt_modify_planned_flight_conflict(
        self,
    ) -> Optional[OperationalIntentReference]:
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate Flight 1 sharing",
            self._intents_extent,
        ) as validator:
            self.begin_test_step("Plan Flight 1")
            resp_flight_1, self.flight1_id, _ = plan_flight_intent(
                self,
                self.tested_uss,
                self.flight1_planned.request,
            )
            self.end_test_step()
            flight_1_oi_ref = validator.expect_shared(self.flight1_planned.request)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate Flight 2 sharing",
            self._intents_extent,
        ) as validator:
            self.begin_test_step("Plan Flight 2")
            resp_flight_2, self.flight2_id, _ = plan_flight_intent(
                self,
                self.control_uss,
                self.flight2_planned.request,
            )
            self.end_test_step()
            validator.expect_shared(self.flight2_planned.request)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate Flight 1 not modified",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            self.begin_test_step("Attempt to modify planned Flight 1 in conflict")
            _ = modify_planned_priority_conflict_flight_intent(
                self,
                self.tested_uss,
                self.flight1m_planned.request,
                self.flight1_id,
            )
            self.end_test_step()
            flight_1_oi_ref = validator.expect_shared(
                self.flight1_planned.request, skip_if_not_found=True
            )

        return flight_1_oi_ref

    def _attempt_activate_flight_conflict(
        self, flight_1_oi_ref: Optional[OperationalIntentReference]
    ) -> Optional[OperationalIntentReference]:
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate Flight 1 not activated",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            self.begin_test_step("Attempt to activate conflicting Flight 1")
            _ = activate_priority_conflict_flight_intent(
                self,
                self.tested_uss,
                self.flight1_activated.request,
                self.flight1_id,
            )
            self.end_test_step()
            flight_1_oi_ref = validator.expect_shared(
                self.flight1_planned.request, skip_if_not_found=True
            )

        return flight_1_oi_ref

    def _modify_activated_flight_conflict_preexisting(
        self, flight_1_oi_ref: Optional[OperationalIntentReference]
    ) -> Tuple[FlightIntent, OperationalIntentReference, OperationalIntentReference]:
        _ = delete_flight_intent(
            self, "Delete Flight 2", self.control_uss, self.flight2_id
        )
        self.flight2_id = None

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate Flight 1 sharing",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            activate_flight_intent(
                self,
                "Activate Flight 1",
                self.tested_uss,
                self.flight1_activated.request,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(self.flight1_activated.request)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate Flight 2 sharing",
            self._intents_extent,
        ) as validator:
            self.begin_test_step("Plan Flight 2")
            _, self.flight2_id, _ = plan_flight_intent(
                self,
                self.control_uss,
                self.flight2_planned.request,
            )
            self.end_test_step()
            flight_2_oi_ref = validator.expect_shared(self.flight2_planned.request)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate Flight 2 sharing",
            self._intents_extent,
            flight_2_oi_ref,
        ) as validator:
            activate_flight_intent(
                self,
                "Activate Flight 2",
                self.control_uss,
                self.flight2_activated.request,
                self.flight2_id,
            )
            flight_2_oi_ref = validator.expect_shared(self.flight2_activated.request)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate Flight 1 sharing",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            resp = modify_activated_flight_intent(
                self,
                "Modify activated Flight 1 in conflict with activated Flight 2",
                self.tested_uss,
                self.flight1m_activated.request,
                self.flight1_id,
                preexisting_conflict=True,
            )

            if resp.result == InjectFlightResponseResult.ReadyToFly:
                flight_1_oi_ref = validator.expect_shared(
                    self.flight1m_activated.request
                )
                return self.flight1m_activated, flight_1_oi_ref, flight_2_oi_ref
            else:
                flight_1_oi_ref = validator.expect_shared(
                    self.flight1_activated.request
                )
                return self.flight1_activated, flight_1_oi_ref, flight_2_oi_ref

    def _attempt_modify_activated_flight_conflict(
        self,
        flight_1_intent: FlightIntent,
        flight_1_oi_ref: OperationalIntentReference,
        flight_2_oi_ref: OperationalIntentReference,
    ):
        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            "Validate Flight 2 sharing",
            self._intents_extent,
            flight_2_oi_ref,
        ) as validator:
            modify_activated_flight_intent(
                self,
                "Modify activated Flight 2 to not conflict with activated Flight 1",
                self.control_uss,
                self.flight2m_activated.request,
                self.flight2_id,
            )
            validator.expect_shared(self.flight2m_activated.request)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate Flight 1 not modified",
            self._intents_extent,
            flight_1_oi_ref,
        ) as validator:
            self.begin_test_step("Attempt to modify activated Flight 1 in conflict")
            modify_activated_priority_conflict_flight_intent(
                self,
                self.tested_uss,
                self.flight1c_activated.request,
                self.flight1_id,
            )
            self.end_test_step()
            validator.expect_shared(
                flight_1_intent.request,
                skip_if_not_found=True,
            )

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.control_uss, self.tested_uss))
        self.end_cleanup()
