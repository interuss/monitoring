import arrow
from uas_standards.astm.f3548.v21.api import OperationalIntentReference
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.clients.flight_planning import flight_info
from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
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
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import (
    MockUSSClient,
    MockUSSResource,
)
from monitoring.uss_qualifier.scenarios.astm.utm.subscription_notifications.test_steps.validate_notification_received import (
    expect_tested_uss_receives_notification_from_mock_uss,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import OpIntentValidator
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    activate_flight,
    cleanup_flights,
    modify_planned_flight,
    plan_flight,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class ReceiveNotificationsForAwareness(TestScenario):
    flight_1_planned: FlightInfoTemplate
    flight_2_planned: FlightInfoTemplate
    flight_2_planned_modified: FlightInfoTemplate
    flight_1_activated: FlightInfoTemplate

    tested_uss_client: FlightPlannerClient
    mock_uss: MockUSSClient
    mock_uss_client: FlightPlannerClient
    dss: DSSInstance

    flight_1_id: str
    flight_1_oi_ref: OperationalIntentReference
    flight_2_id: str
    flight_2_oi_ref: OperationalIntentReference

    def __init__(
        self,
        tested_uss: FlightPlannerResource,
        mock_uss: MockUSSResource,
        dss: DSSInstanceResource,
        flight_intents: FlightIntentsResource | None = None,
    ):
        super().__init__()
        self.tested_uss_client = tested_uss.client
        self.mock_uss = mock_uss.mock_uss
        self.mock_uss_client = mock_uss.mock_uss.flight_planner
        self.dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "search for operational intent references to verify outcomes of planning activities"
            }
        )

        expected_flight_intents = [
            ExpectedFlightIntent(
                "flight_1_planned",
                "Flight 1",
                must_not_conflict_with=["Flight 2"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight_1_activated",
                "Flight 1",
                must_not_conflict_with=["Flight 2"],
                usage_state=AirspaceUsageState.InUse,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight_2_planned",
                "Flight 2",
                must_not_conflict_with=["Flight 1"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight_2_planned_modified",
                "Flight 2",
                must_not_conflict_with=["Flight 1"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
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

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.record_note(
            "Tested USS",
            f"{self.tested_uss_client.participant_id}",
        )
        self.record_note(
            "Mock USS",
            f"{self.mock_uss_client.participant_id}",
        )
        self.begin_test_case(
            "Activated operational intent receives notification of relevant intent"
        )
        self._receive_notification_successfully_when_activated_test_case()
        self.end_test_case()

        self.begin_test_case(
            "Modify Activated operational intent area and receive notification of relevant intent"
        )
        self._receive_notification_successfully_when_activated_modified_test_case()
        self.end_test_case()

        self.end_test_scenario()

    def _receive_notification_successfully_when_activated_test_case(self):
        self.time_context.evaluate_now()

        flight_1_planned = self.flight_1_planned.resolve(self.time_context)
        flight_1_activated = self.flight_1_activated.resolve(self.time_context)
        flight_2_planned = self.flight_2_planned.resolve(self.time_context)

        resolved_extents = flight_info.extents_of(
            [flight_1_planned, flight_1_activated, flight_2_planned]
        ).to_f3548v21()

        self.begin_test_step("Tested_uss plans and activates Flight 1")
        with OpIntentValidator(
            self,
            self.tested_uss_client,
            self.dss,
            resolved_extents,
        ) as validator:
            _, self.flight_1_id, as_planned = plan_flight(
                self,
                self.tested_uss_client,
                flight_1_planned,
            )
            # TODO(#1326): Validate that flight as planned still allows this scenario to proceed
            flight_1_planned = as_planned
            self.flight_1_oi_ref = validator.expect_shared(flight_1_planned)

        with OpIntentValidator(
            self,
            self.tested_uss_client,
            self.dss,
            resolved_extents,
            self.flight_1_oi_ref,
        ) as validator:
            _, self.flight_1_id, as_planned = activate_flight(
                self,
                self.tested_uss_client,
                flight_1_activated,
                self.flight_1_id,
            )
            # TODO(#1326): Validate that flight as planned still allows this scenario to proceed
            flight_1_activated = as_planned
            self.flight_1_oi_ref = validator.expect_shared(flight_1_activated)

        self.end_test_step()

        self.begin_test_step("Mock_uss plans Flight 2")
        with OpIntentValidator(
            self,
            self.mock_uss_client,
            self.dss,
            resolved_extents,
        ) as validator:
            flight_2_planning_time = arrow.utcnow().datetime
            _, self.flight_2_id, as_planned = plan_flight(
                self,
                self.mock_uss_client,
                flight_2_planned,
            )
            # TODO(#1326): Validate that flight as planned still allows this scenario to proceed
            flight_2_planned = as_planned
            self.flight_2_oi_ref = validator.expect_shared(flight_2_planned)

        self.end_test_step()

        self.begin_test_step("Validate Flight 2 notification received by tested_uss")
        expect_tested_uss_receives_notification_from_mock_uss(
            self,
            self.mock_uss,
            flight_2_planning_time,
            self.flight_2_oi_ref.id,
            self.flight_1_oi_ref.subscription_id,
            self.flight_1_oi_ref.uss_base_url,
            self.tested_uss_client.participant_id,
            flight_2_planning_time,
        )
        self.end_test_step()

    def _receive_notification_successfully_when_activated_modified_test_case(self):
        flight_2_planned_modified = self.flight_2_planned_modified.resolve(
            self.time_context.evaluate_now()
        )

        self.begin_test_step("Mock_uss modifies planned Flight 2")
        with OpIntentValidator(
            self,
            self.mock_uss_client,
            self.dss,
            flight_2_planned_modified.basic_information.area.bounding_volume.to_f3548v21(),
            self.flight_2_oi_ref,
        ) as validator:
            flight_2_modif_time = arrow.utcnow().datetime
            _, as_planned = modify_planned_flight(
                self,
                self.mock_uss_client,
                flight_2_planned_modified,
                self.flight_2_id,
            )
            # TODO(#1326): Validate that flight as planned still allows this scenario to proceed
            flight_2_planned_modified = as_planned
            self.flight_2_oi_ref = validator.expect_shared(flight_2_planned_modified)

        self.end_test_step()

        self.begin_test_step("Validate Flight 2 notification received by tested_uss")
        expect_tested_uss_receives_notification_from_mock_uss(
            self,
            self.mock_uss,
            flight_2_modif_time,
            self.flight_2_oi_ref.id,
            self.flight_1_oi_ref.subscription_id,
            self.flight_1_oi_ref.uss_base_url,
            self.tested_uss_client.participant_id,
            flight_2_modif_time,
        )
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.mock_uss_client, self.tested_uss_client))
        self.end_cleanup()
