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
from monitoring.uss_qualifier.scenarios.astm.utm.notifications_to_operator.notification_checker import (
    NotificationChecker,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import OpIntentValidator
from monitoring.uss_qualifier.scenarios.flight_planning.prioritization_test_steps import (
    activate_priority_conflict_flight,
    modify_activated_priority_conflict_flight,
    modify_planned_priority_conflict_flight,
    plan_priority_conflict_flight,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    activate_flight,
    cleanup_flights,
    delete_flight,
    modify_activated_flight,
    plan_flight,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class ConflictHigherPriority(TestScenario, NotificationChecker):
    times: dict[TimeDuringTest, Time]

    flight1_id: str | None = None
    flight1_planned: FlightInfoTemplate
    flight1m_planned: FlightInfoTemplate
    flight1_activated: FlightInfoTemplate
    flight1m_activated: FlightInfoTemplate
    flight1c_activated: FlightInfoTemplate

    flight2_id: str | None = None
    flight2_planned: FlightInfoTemplate
    flight2_activated: FlightInfoTemplate
    flight2m_activated: FlightInfoTemplate

    tested_uss: FlightPlannerClient
    control_uss: FlightPlannerClient
    dss: DSSInstance

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        tested_uss: FlightPlannerResource,
        control_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
    ):
        super().__init__()
        self.tested_uss = tested_uss.client
        self.control_uss = control_uss.client
        self.dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "search for operational intent references to verify outcomes of planning activities and retrieve operational intent details"
            }
        )

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
        self.record_note(
            "Control USS",
            f"{self.control_uss.participant_id}",
        )

        self.begin_test_case("Attempt to plan flight in conflict")
        self._attempt_plan_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to modify planned flight in conflict")
        (
            flight_1_oi_ref,
            flight_1_intent,
        ) = self._attempt_modify_planned_flight_conflict()
        self.end_test_case()

        self.begin_test_case("Attempt to activate flight in conflict")
        flight_1_oi_ref = self._attempt_activate_flight_conflict(
            flight_1_oi_ref, flight_1_intent
        )
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
            validator.expect_shared(flight2_planned)
        self.end_test_step()

        self.begin_test_step("Attempt to plan Flight 1")
        flight1_planned = self.resolve_flight(self.flight1_planned)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            flight1_planned,
        ) as validator:
            plan_priority_conflict_flight(
                self,
                self.tested_uss,
                flight1_planned,
            )
            validator.expect_not_shared()
        self.end_test_step()

        self.begin_test_step("Delete Flight 2")
        _ = delete_flight(self, self.control_uss, self.flight2_id)
        self.flight2_id = None
        self.end_test_step()

    def _attempt_modify_planned_flight_conflict(
        self,
    ) -> tuple[OperationalIntentReference | None, FlightInfo]:
        self.begin_test_step("Plan Flight 1")
        flight1_planned = self.resolve_flight(self.flight1_planned)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            flight1_planned,
        ) as validator:
            _, self.flight1_id = plan_flight(
                self,
                self.tested_uss,
                flight1_planned,
            )
            flight_1_oi_ref = validator.expect_shared(flight1_planned)
        self.end_test_step()

        self.begin_test_step("Plan Flight 2")
        preexisting_notifications = self._get_preexisting_notifications(
            [self.control_uss, self.tested_uss]
        )
        flight2_planned = self.resolve_flight(self.flight2_planned)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            flight2_planned,
        ) as validator:
            earliest_creation_time = arrow.utcnow().datetime
            _, self.flight2_id = plan_flight(
                self,
                self.control_uss,
                flight2_planned,
            )
            latest_creation_time = arrow.utcnow().datetime
            validator.expect_shared(flight2_planned)
        self.end_test_step()

        self.begin_test_step("Check for conflict notifications")
        self._check_for_user_notifications(
            causing_conflict=self.control_uss,
            observing_conflict=self.tested_uss,
            preexisting_notifications=preexisting_notifications,
            earliest_action_time=earliest_creation_time,
            latest_action_time=latest_creation_time,
        )
        self.end_test_step()

        self.begin_test_step("Attempt to modify planned Flight 1 in conflict")
        flight1m_planned = self.resolve_flight(self.flight1m_planned)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            [flight1_planned, flight1m_planned],
            flight_1_oi_ref,
        ) as validator:
            modify_planned_priority_conflict_flight(
                self,
                self.tested_uss,
                flight1m_planned,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                flight1_planned, skip_if_not_found=True
            )
        self.end_test_step()

        return flight_1_oi_ref, flight1_planned

    def _attempt_activate_flight_conflict(
        self,
        flight_1_oi_ref: OperationalIntentReference | None,
        flight_1_intent: FlightInfo,
    ) -> OperationalIntentReference | None:
        self.begin_test_step("Attempt to activate conflicting Flight 1")
        flight1_activated = self.resolve_flight(self.flight1_activated)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            [flight_1_intent, flight1_activated],
            flight_1_oi_ref,
        ) as validator:
            activate_priority_conflict_flight(
                self,
                self.tested_uss,
                flight1_activated,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(
                flight_1_intent, skip_if_not_found=True
            )
        self.end_test_step()

        return flight_1_oi_ref

    def _modify_activated_flight_conflict_preexisting(
        self, flight_1_oi_ref: OperationalIntentReference | None
    ) -> tuple[FlightInfo, OperationalIntentReference, OperationalIntentReference]:
        self.begin_test_step("Delete Flight 2")
        _ = delete_flight(self, self.control_uss, self.flight2_id)
        self.flight2_id = None
        self.end_test_step()

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
                self.tested_uss,
                flight1_activated,
                self.flight1_id,
            )
            flight_1_oi_ref = validator.expect_shared(flight1_activated)
        self.end_test_step()

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
        preexisting_notifications = self._get_preexisting_notifications(
            [self.control_uss, self.tested_uss]
        )
        flight2_activated = self.resolve_flight(self.flight2_activated)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            flight2_activated,
            flight_2_oi_ref,
        ) as validator:
            earliest_activation_time = arrow.utcnow().datetime
            activate_flight(
                self,
                self.control_uss,
                flight2_activated,
                self.flight2_id,
            )
            latest_activation_time = arrow.utcnow().datetime
            flight_2_oi_ref = validator.expect_shared(flight2_activated)
        self.end_test_step()

        self.begin_test_step("Check for conflict notifications")
        self._check_for_user_notifications(
            causing_conflict=self.control_uss,
            observing_conflict=self.tested_uss,
            preexisting_notifications=preexisting_notifications,
            earliest_action_time=earliest_activation_time,
            latest_action_time=latest_activation_time,
        )
        self.end_test_step()

        self.begin_test_step(
            "Modify activated Flight 1 in conflict with activated Flight 2"
        )
        flight1m_activated = self.resolve_flight(self.flight1m_activated)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            [flight1_activated, flight1m_activated],
            flight_1_oi_ref,
        ) as validator:
            resp = modify_activated_flight(
                self,
                self.tested_uss,
                flight1m_activated,
                self.flight1_id,
                preexisting_conflict=True,
            )

            if resp.activity_result == PlanningActivityResult.Completed:
                flight_1_oi_ref = validator.expect_shared(flight1m_activated)
                result = (flight1m_activated, flight_1_oi_ref, flight_2_oi_ref)
            else:
                flight_1_oi_ref = validator.expect_shared(flight1_activated)
                result = (flight1_activated, flight_1_oi_ref, flight_2_oi_ref)
        self.end_test_step()
        return result

    def _attempt_modify_activated_flight_conflict(
        self,
        flight_1_intent: FlightInfo,
        flight_1_oi_ref: OperationalIntentReference,
        flight_2_oi_ref: OperationalIntentReference,
    ):
        self.begin_test_step(
            "Modify activated Flight 2 to not conflict with activated Flight 1"
        )
        flight2m_activated = self.resolve_flight(self.flight2m_activated)

        with OpIntentValidator(
            self,
            self.control_uss,
            self.dss,
            flight2m_activated,
            flight_2_oi_ref,
        ) as validator:
            resp = modify_activated_flight(
                self,
                self.control_uss,
                flight2m_activated,
                self.flight2_id,
            )
            if resp.activity_result == PlanningActivityResult.Completed:
                validator.expect_shared(flight2m_activated)
        self.end_test_step()

        if resp.activity_result == PlanningActivityResult.NotSupported:
            self.record_note(
                "conflict_higher_priority_skip_step",
                f"Skip next step since USS {self.control_uss} did not modify flight 2.",
            )
            return

        self.begin_test_step("Attempt to modify activated Flight 1 in conflict")
        flight1c_activated = self.resolve_flight(self.flight1c_activated)

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            [flight_1_intent, flight1c_activated],
            flight_1_oi_ref,
        ) as validator:
            modify_activated_priority_conflict_flight(
                self,
                self.tested_uss,
                flight1c_activated,
                self.flight1_id,
            )
            validator.expect_shared(
                flight_1_intent,
                skip_if_not_found=True,
            )
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.control_uss, self.tested_uss))
        self.end_cleanup()
