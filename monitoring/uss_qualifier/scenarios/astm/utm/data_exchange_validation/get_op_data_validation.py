from typing import Optional, Dict

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.clients.mock_uss.interactions import QueryDirection
from monitoring.monitorlib.temporal import TimeDuringTest
import arrow
from monitoring.monitorlib.temporal import Time
from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntent,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerResource,
)
from monitoring.monitorlib.geotemporal import Volume4DCollection

from monitoring.uss_qualifier.resources.interuss.mock_uss.client import (
    MockUSSClient,
    MockUSSResource,
)
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.invalid_op_test_steps import (
    plan_flight_intent_expect_failed,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    OpIntentValidator,
    OpIntentValidationFailureType,
)
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.expected_interactions_test_steps import (
    expect_no_interuss_post_interactions,
    expect_mock_uss_receives_op_intent_notification,
    mock_uss_interactions,
    is_op_intent_notification_with_id,
)
from monitoring.monitorlib.clients.mock_uss.mock_uss_scd_injection_api import (
    MockUssFlightBehavior,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    ScenarioCannotContinueError,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    cleanup_flights_fp_client,
    plan_flight,
    delete_flight,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.astm.f3548.v21.api import OperationID


class GetOpResponseDataValidationByUSS(TestScenario):
    flight_1: FlightInfoTemplate
    flight_2: FlightInfoTemplate

    tested_uss_client: FlightPlannerClient
    mock_uss: MockUSSClient
    mock_uss_client: FlightPlannerClient
    dss: DSSInstance

    def __init__(
        self,
        tested_uss: FlightPlannerResource,
        mock_uss: MockUSSResource,
        dss: DSSInstanceResource,
        flight_intents: Optional[FlightIntentsResource] = None,
    ):
        super().__init__()
        self.tested_uss_client = tested_uss.client
        self.mock_uss = mock_uss.mock_uss
        self.mock_uss_client = mock_uss.mock_uss.flight_planner
        self.dss = dss.dss

        if not flight_intents:
            msg = f"No FlightIntentsResource was provided as input to this test, it is assumed that the jurisdiction does not allow any same priority conflicts, execution of the scenario was stopped without failure"
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

        extents = []
        for efi in expected_flight_intents:
            intent = FlightIntent.from_flight_info_template(templates[efi.intent_id])
            extents.extend(intent.request.operational_intent.volumes)
            extents.extend(intent.request.operational_intent.off_nominal_volumes)
            setattr(self, efi.intent_id, templates[efi.intent_id])

        self._intents_extent = Volume4DCollection.from_interuss_scd_api(
            extents
        ).bounding_volume.to_f3548v21()

    def run(self, context: ExecutionContext):
        times = {
            TimeDuringTest.StartOfTestRun: Time(context.start_time),
            TimeDuringTest.StartOfScenario: Time(arrow.utcnow().datetime),
        }
        self.begin_test_scenario(context)

        self.record_note(
            "Tested USS",
            f"{self.tested_uss_client.participant_id}",
        )
        self.record_note(
            "Control USS",
            f"{self.mock_uss_client.participant_id}",
        )

        self.begin_test_case("Successfully plan flight near an existing flight")
        self._plan_successfully_test_case(times)
        self.end_test_case()

        self.begin_test_case("Flight planning prevented due to invalid data sharing")
        self._plan_unsuccessfully_test_case(times)
        self.end_test_case()

        self.end_test_scenario()

    def _plan_successfully_test_case(self, times: Dict[TimeDuringTest, Time]):
        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        flight_2 = self.flight_2.resolve(times)

        with OpIntentValidator(
            self,
            self.mock_uss_client,
            self.dss,
            "Validate flight 2 sharing",
            self._intents_extent,
        ) as validator:
            self.begin_test_step("mock_uss plans flight 2")
            flight_2_planning_time = Time(arrow.utcnow().datetime)
            _, self.flight_2_id = plan_flight(
                self,
                self.mock_uss_client,
                flight_2,
            )
            self.end_test_step()

            flight_2_oi_ref = validator.expect_shared(flight_2)

        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        flight_1 = self.flight_1.resolve(times)

        with OpIntentValidator(
            self,
            self.tested_uss_client,
            self.dss,
            "Validate flight 1 sharing",
            self._intents_extent,
        ) as validator:
            self.begin_test_step("tested_uss plans flight 1")
            flight_1_planning_time = Time(arrow.utcnow().datetime)
            plan_res, self.flight_1_id = plan_flight(
                self,
                self.tested_uss_client,
                flight_1,
            )
            self.end_test_step()
            validator.expect_shared(
                flight_1,
            )

        self.begin_test_step(
            "Check for notification to tested_uss due to subscription in flight 2 area"
        )
        tested_uss_notifications, _ = mock_uss_interactions(
            scenario=self,
            mock_uss=self.mock_uss,
            op_id=OperationID.NotifyOperationalIntentDetailsChanged,
            direction=QueryDirection.Outgoing,
            since=flight_2_planning_time,
            is_applicable=is_op_intent_notification_with_id(flight_2_oi_ref.id),
        )
        self.end_test_step()

        self.begin_test_step("Validate flight2 GET interaction, if no notification")
        if not tested_uss_notifications:
            tested_uss_get_requests, query = mock_uss_interactions(
                scenario=self,
                mock_uss=self.mock_uss,
                op_id=OperationID.GetOperationalIntentDetails,
                direction=QueryDirection.Incoming,
                since=flight_1_planning_time,
                query_params={"entity_id": flight_2_oi_ref.id},
            )
            with self.check(
                "Expect GET request when no notification",
                [self.tested_uss_client.participant_id],
            ) as check:
                if not tested_uss_get_requests:
                    check.record_failed(
                        summary=f"mock_uss did not GET op intent details when planning",
                        details=f"mock_uss did not receive a request to GET operational intent details for operational intent {flight_2_oi_ref.id}. tested_uss was not sent a notification with the operational intent details, so they should have requested the operational intent details during planning.",
                        query_timestamps=[query.request.timestamp],
                    )
        else:
            self.record_note(
                "No flight 2a GET expected reason",
                f"Notifications found to {', '.join(n.query.request.url for n in tested_uss_notifications)}",
            )
        self.end_test_step()

        self.begin_test_step("Validate flight1 Notification sent to mock_uss")
        expect_mock_uss_receives_op_intent_notification(
            self,
            self.mock_uss,
            flight_1_planning_time,
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

    def _plan_unsuccessfully_test_case(self, times: Dict[TimeDuringTest, Time]):
        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        flight_info = self.flight_2.resolve(times)

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
        with OpIntentValidator(
            self,
            self.mock_uss_client,
            self.dss,
            "Validate flight 2 shared operational intent with invalid data",
            self._intents_extent,
        ) as validator:
            self.begin_test_step(
                "mock_uss plans flight 2, sharing invalid operational intent data"
            )
            flight_2_planning_time = Time(arrow.utcnow().datetime)
            _, self.flight_2_id = plan_flight(
                self,
                self.mock_uss_client,
                flight_info,
                additional_fields,
            )
            self.end_test_step()
            flight_2_oi_ref = validator.expect_shared_with_invalid_data(
                flight_info,
                validation_failure_type=OpIntentValidationFailureType.DataFormat,
                invalid_fields=[modify_field1, modify_field2],
            )

        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        flight_1 = self.flight_1.resolve(times)
        with OpIntentValidator(
            self,
            self.tested_uss_client,
            self.dss,
            "Validate flight 1 not shared by tested_uss",
            self._intents_extent,
        ) as validator:
            self.begin_test_step("tested_uss attempts to plan flight 1, expect failure")
            flight_1_planning_time = Time(arrow.utcnow().datetime)
            _, self.flight_1_id = plan_flight_intent_expect_failed(
                self,
                self.tested_uss_client,
                flight_1,
            )
            self.end_test_step()
            validator.expect_not_shared()

        self.begin_test_step(
            "Check for notification to tested_uss due to subscription in flight 2 area"
        )
        tested_uss_notifications, _ = mock_uss_interactions(
            scenario=self,
            mock_uss=self.mock_uss,
            op_id=OperationID.NotifyOperationalIntentDetailsChanged,
            direction=QueryDirection.Outgoing,
            since=flight_2_planning_time,
            is_applicable=is_op_intent_notification_with_id(flight_2_oi_ref.id),
        )
        self.end_test_step()

        self.begin_test_step("Validate flight2 GET interaction, if no notification")
        if not tested_uss_notifications:
            tested_uss_get_requests, query = mock_uss_interactions(
                scenario=self,
                mock_uss=self.mock_uss,
                op_id=OperationID.GetOperationalIntentDetails,
                direction=QueryDirection.Incoming,
                since=flight_1_planning_time,
                query_params={"entity_id": flight_2_oi_ref.id},
            )
            with self.check(
                "Expect GET request when no notification",
                [self.tested_uss_client.participant_id],
            ) as check:
                if not tested_uss_get_requests:
                    check.record_failed(
                        summary=f"mock_uss did not GET op intent details when planning",
                        details=f"mock_uss did not receive a request to GET operational intent details for operational intent {flight_2_oi_ref.id}. tested_uss was not sent a notification with the operational intent details, so they should have requested the operational intent details during planning.",
                        query_timestamps=[query.request.timestamp],
                    )
        else:
            self.record_note(
                "No flight 2b GET expected reason",
                f"Notifications found to {', '.join(n.query.request.url for n in tested_uss_notifications)}",
            )
        self.end_test_step()

        self.begin_test_step("Validate flight 1 Notification not sent to mock_uss")
        expect_no_interuss_post_interactions(
            self,
            self.mock_uss,
            flight_1_planning_time,
            self.tested_uss_client.participant_id,
        )
        self.end_test_step()

        self.begin_test_step("Delete mock_uss flight")
        delete_flight(self, self.mock_uss_client, self.flight_2_id)
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights_fp_client(self, (self.mock_uss_client, self.tested_uss_client)),
        self.end_cleanup()
