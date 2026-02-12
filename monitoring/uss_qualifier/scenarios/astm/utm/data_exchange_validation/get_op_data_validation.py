import arrow
from uas_standards.astm.f3548.v21.api import EntityID
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    FlightPlanStatus,
    PlanningActivityResult,
)
from monitoring.monitorlib.clients.mock_uss.mock_uss_scd_injection_api import (
    MockUssFlightBehavior,
)
from monitoring.monitorlib.temporal import Time
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
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.expected_interactions_test_steps import (
    expect_mock_uss_receives_op_intent_notification,
    expect_no_interuss_post_interactions,
    expect_uss_obtained_op_intent_details,
)
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.wait import (
    MaxTimeToWaitForSubscriptionNotificationSeconds as max_wait_time,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    OpIntentValidationFailureType,
    OpIntentValidator,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
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


class GetOpResponseDataValidationByUSS(TestScenario):
    flight_1: FlightInfoTemplate
    flight_2: FlightInfoTemplate

    op_intent_ids: set[EntityID]

    tested_uss_client: FlightPlannerClient
    mock_uss: MockUSSClient
    mock_uss_client: FlightPlannerClient
    dss: DSSInstance

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

        if not flight_intents:
            msg = "No FlightIntentsResource was provided as input to this test, it is assumed that the jurisdiction does not allow any same priority conflicts, execution of the scenario was stopped without failure"
            self.record_note(
                "Jurisdiction of tested USS does not allow any same priority conflicts",
                msg,
            )
            raise ScenarioCannotContinueError(msg)

        expected_flight_intents = [
            ExpectedFlightIntent(
                "flight_1",
                "Flight 1",
                must_not_conflict_with=["Flight 2"],
                f3548v21_priority_equal_to=["Flight 2"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
                # TODO: Must intersect bounding box of Flight 2
            ),
            ExpectedFlightIntent(
                "flight_2",
                "Flight 2",
                must_not_conflict_with=["Flight 1"],
                f3548v21_priority_equal_to=["Flight 1"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
                # TODO: Must intersect bounding box of Flight 1
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
        self.op_intent_ids = set()
        self.begin_test_scenario(context)

        self.record_note(
            "Tested USS",
            f"{self.tested_uss_client.participant_id}",
        )

        self.begin_test_case("Successfully plan flight near an existing flight")
        self._plan_successfully_test_case()
        self.end_test_case()

        self.begin_test_case("Flight planning prevented due to invalid data sharing")
        self._plan_unsuccessfully_test_case()
        self.end_test_case()

        self.end_test_scenario()

    def _plan_successfully_test_case(self):
        flight_2 = self.flight_2.resolve(self.time_context.evaluate_now())

        self.begin_test_step("mock_uss plans flight 2")
        with OpIntentValidator(
            self,
            self.mock_uss_client,
            self.dss,
            flight_2.basic_information.area.bounding_volume.to_f3548v21(),
        ) as validator:
            flight_2_planning_time = Time(arrow.utcnow().datetime)
            _, self.flight_2_id = plan_flight(
                self,
                self.mock_uss_client,
                flight_2,
            )

            flight_2_oi_ref = validator.expect_shared(flight_2)
            self.op_intent_ids.add(flight_2_oi_ref.id)
        self.end_test_step()

        flight_1 = self.flight_1.resolve(self.time_context.evaluate_now())

        self.begin_test_step("tested_uss plans flight 1")
        with OpIntentValidator(
            self,
            self.tested_uss_client,
            self.dss,
            flight_1.basic_information.area.bounding_volume.to_f3548v21(),
        ) as validator:
            flight_1_planning_time = Time(arrow.utcnow().datetime)
            plan_res, self.flight_1_id = plan_flight(
                self,
                self.tested_uss_client,
                flight_1,
            )
            flight_1_oi_ref = validator.expect_shared(flight_1)
            self.op_intent_ids.add(flight_1_oi_ref.id)
        self.end_test_step()

        self.begin_test_step("Validate that tested_uss obtained flight2 details")
        self.sleep(
            max_wait_time,
            "we have to wait the longest it may take a USS to send a notification before we can establish another USS has obtained operational intent details",
        )
        expect_uss_obtained_op_intent_details(
            self,
            self.mock_uss,
            flight_2_planning_time,
            flight_2_oi_ref.id,
            self.tested_uss_client.participant_id,
        )
        self.end_test_step()

        self.begin_test_step("Validate flight1 Notification sent to mock_uss")
        expect_mock_uss_receives_op_intent_notification(
            self,
            self.mock_uss,
            flight_1_planning_time,
            flight_1_oi_ref.id,
            self.tested_uss_client.participant_id,
            plan_res.queries[0].request.timestamp,
        )
        self.end_test_step()

        self.begin_test_step("Delete tested_uss flight")
        delete_flight(self, self.tested_uss_client, self.flight_1_id)
        self.end_test_step()

        self.begin_test_step("Delete mock_uss flight")
        delete_flight(self, self.mock_uss_client, self.flight_2_id)
        self.end_test_step()

    def _plan_unsuccessfully_test_case(self):
        flight_info = self.flight_2.resolve(self.time_context.evaluate_now())

        modify_field1 = "state"
        modify_field2 = "priority"
        # Modifying the request with invalid data
        behavior = MockUssFlightBehavior(
            modify_sharing_methods=["GET", "POST"],
            modify_fields={
                "reference": {modify_field1: "Flying"},
                "details": {modify_field2: 1.2},
            },
        )

        additional_fields = {"behavior": behavior}
        self.begin_test_step(
            "mock_uss plans flight 2, sharing invalid operational intent data"
        )
        with OpIntentValidator(
            self,
            self.mock_uss_client,
            self.dss,
            flight_info.basic_information.area.bounding_volume.to_f3548v21(),
        ) as validator:
            flight_2_planning_time = Time(arrow.utcnow().datetime)
            _, self.flight_2_id = plan_flight(
                self,
                self.mock_uss_client,
                flight_info,
                additional_fields,
            )
            flight_2_oi_ref = validator.expect_shared_with_invalid_data(
                flight_info,
                validation_failure_type=OpIntentValidationFailureType.DataFormat,
                invalid_fields=[modify_field1, modify_field2],
            )
            self.op_intent_ids.add(flight_2_oi_ref.id)
        self.end_test_step()

        flight_1 = self.flight_1.resolve(self.time_context.evaluate_now())
        self.begin_test_step("tested_uss attempts to plan flight 1, expect failure")
        with OpIntentValidator(
            self,
            self.tested_uss_client,
            self.dss,
            flight_1.basic_information.area.bounding_volume.to_f3548v21(),
        ) as validator:
            flight_1_planning_time = Time(arrow.utcnow().datetime)
            _, self.flight_1_id = submit_flight(
                self,
                "Plan should fail",
                {
                    (PlanningActivityResult.Failed, FlightPlanStatus.NotPlanned),
                    (PlanningActivityResult.Rejected, FlightPlanStatus.NotPlanned),
                },
                {},
                self.tested_uss_client,
                flight_1,
            )
            validator.expect_not_shared()
        self.end_test_step()

        self.begin_test_step("Validate that tested_uss obtained flight2 details")
        self.sleep(
            max_wait_time,
            "we have to wait the longest it may take a USS to send a notification before we can establish another USS has obtained operational intent details",
        )
        expect_uss_obtained_op_intent_details(
            self,
            self.mock_uss,
            flight_2_planning_time,
            flight_2_oi_ref.id,
            self.tested_uss_client.participant_id,
        )
        self.end_test_step()

        self.begin_test_step("Validate flight 1 Notification not sent to mock_uss")
        expect_no_interuss_post_interactions(
            self,
            self.mock_uss,
            flight_1_planning_time,
            self.op_intent_ids,
            self.tested_uss_client.participant_id,
        )
        self.end_test_step()

        self.begin_test_step("Delete mock_uss flight")
        delete_flight(self, self.mock_uss_client, self.flight_2_id)
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        (cleanup_flights(self, (self.mock_uss_client, self.tested_uss_client)),)
        self.end_cleanup()
