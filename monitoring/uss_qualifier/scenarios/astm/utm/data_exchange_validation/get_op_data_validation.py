from typing import Optional
from urllib.parse import urlsplit

from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntent,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerResource,
)
from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import (
    MockUSSClient,
    MockUSSResource,
)
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.invalid_op_test_steps import (
    InvalidOpIntentSharingValidator,
    plan_flight_intent_expect_failed,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import OpIntentValidator
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.expected_interactions_test_steps import (
    expect_interuss_post_interactions,
    expect_interuss_get_interactions,
    expect_no_interuss_post_interactions,
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
from implicitdict import StringBasedDateTime
from datetime import datetime


class GetOpResponseDataValidationByUSS(TestScenario):
    flight_1: FlightIntent
    flight_2: FlightIntent

    tested_uss_client: FlightPlannerClient
    control_uss: MockUSSClient
    control_uss_client: FlightPlannerClient
    dss: DSSInstance

    def __init__(
        self,
        tested_uss: FlightPlannerResource,
        control_uss: MockUSSResource,
        dss: DSSInstanceResource,
        flight_intents: Optional[FlightIntentsResource] = None,
    ):
        super().__init__()
        self.tested_uss_client = tested_uss.client
        self.control_uss = control_uss.mock_uss
        self.control_uss_client = control_uss.mock_uss.flight_planner
        self.dss = dss.dss

        if not flight_intents:
            msg = f"No FlightIntentsResource was provided as input to this test, it is assumed that the jurisdiction of the tested USS ({self.tested_uss.config.participant_id}) does not allow any same priority conflicts, execution of the scenario was stopped without failure"
            self.record_note(
                "Jurisdiction of tested USS does not allow any same priority conflicts",
                msg,
            )
            raise ScenarioCannotContinueError(msg)

        _flight_intents = {
            k: FlightIntent.from_flight_info_template(v)
            for k, v in flight_intents.get_flight_intents().items()
        }

        extents = []
        for intent in _flight_intents.values():
            extents.extend(intent.request.operational_intent.volumes)
            extents.extend(intent.request.operational_intent.off_nominal_volumes)
        self._intents_extent = Volume4DCollection.from_interuss_scd_api(
            extents
        ).bounding_volume.to_f3548v21()

        try:
            (self.flight_1, self.flight_2,) = (
                _flight_intents["flight_1"],
                _flight_intents["flight_2"],
            )

            assert not Volume4DCollection.from_interuss_scd_api(
                self.flight_1.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_interuss_scd_api(
                    self.flight_2.request.operational_intent.volumes
                )
            ), "flight_1 and flight_2 must not intersect"

        except KeyError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: missing flight intent {e}"
            )
        except AssertionError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

    def run(self, context):
        self.begin_test_scenario(context)

        self.record_note(
            "Tested USS",
            f"{self.tested_uss_client.participant_id}",
        )
        self.record_note(
            "Control USS",
            f"{self.control_uss_client.participant_id}",
        )

        self.begin_test_case("Successfully plan flight near an existing flight")
        self._tested_uss_plans_deconflicted_flight_near_existing_flight()
        self.end_test_case()

        self.begin_test_case("Flight planning prevented due to invalid data sharing")
        self._tested_uss_unable_to_plan_flight_near_invalid_shared_existing_flight()
        self.end_test_case()

        self.end_test_scenario()

    def _tested_uss_plans_deconflicted_flight_near_existing_flight(self):

        with OpIntentValidator(
            self,
            self.control_uss_client,
            self.dss,
            "Validate flight 2 sharing",
            self._intents_extent,
        ) as validator:
            _, self.flight_2_id = plan_flight(
                self,
                "Control_uss plans flight 2",
                self.control_uss_client,
                FlightInfo.from_scd_inject_flight_request(self.flight_2.request),
            )

            flight_2_oi_ref = validator.expect_shared(self.flight_2.request)

        self.begin_test_step(
            "Precondition - check tested_uss has no subscription in flight 2 area"
        )
        # ToDo - Add the test step details
        self.end_test_step()

        st = StringBasedDateTime(datetime.utcnow())
        with OpIntentValidator(
            self,
            self.tested_uss_client,
            self.dss,
            "Validate flight 1 sharing",
            self._intents_extent,
        ) as validator:
            _, self.flight_1_id = plan_flight(
                self,
                "Tested_uss plans flight 1",
                self.tested_uss_client,
                FlightInfo.from_scd_inject_flight_request(self.flight_1.request),
            )

            flight_1_oi_ref = validator.expect_shared(
                self.flight_1.request,
            )

        control_uss_domain = "{0.scheme}://{0.netloc}/".format(
            urlsplit(self.control_uss.base_url)
        )
        self.begin_test_step("Validate flight2 GET interaction")
        # ToDo - Add the test step details
        self.end_test_step()

        self.begin_test_step("Validate flight1 Notification sent to Control_uss")
        # ToDo - Add the test step details
        self.end_test_step()

        delete_flight(
            self, "Delete tested_uss flight", self.tested_uss_client, self.flight_1_id
        )
        delete_flight(
            self, "Delete control_uss flight", self.control_uss_client, self.flight_2_id
        )

    def _tested_uss_unable_to_plan_flight_near_invalid_shared_existing_flight(self):
        req = self.flight_2.request
        # Modifying the request with invalid data
        behavior = MockUssFlightBehavior(
            modify_sharing_methods=["GET", "POST"],
            modify_fields={
                "reference": {"state": "Flying"},
                "details": {"priority": -1},
            },
        )

        flight_info = FlightInfo.from_scd_inject_flight_request(req)
        additional_fields = {"behavior": behavior}

        with InvalidOpIntentSharingValidator(
            self,
            self.control_uss_client,
            self.dss,
            "Validate flight 2 shared operational intent with invalid data",
            self._intents_extent,
        ) as validator:
            _, self.flight_2_id = plan_flight(
                self,
                "Control_uss plans flight 2, sharing invalid operational intent data",
                self.control_uss_client,
                flight_info,
                additional_fields,
            )
            flight_2_oi_ref = validator.expect_shared_with_invalid_data(req)

        self.begin_test_step(
            "Precondition - check tested_uss has no subscription in flight 2 area"
        )
        # ToDo - Add the test step details
        self.end_test_step()

        st = StringBasedDateTime(datetime.utcnow())
        with InvalidOpIntentSharingValidator(
            self,
            self.tested_uss_client,
            self.dss,
            "Validate flight 1 not shared by tested_uss",
            self._intents_extent,
        ) as validator:
            _, self.flight_1_id = plan_flight_intent_expect_failed(
                self,
                "Tested_uss attempts to plan flight 1, expect failure",
                self.tested_uss_client,
                FlightInfo.from_scd_inject_flight_request(self.flight_1.request),
            )
            validator.expect_not_shared()

        control_uss_domain = "{0.scheme}://{0.netloc}/".format(
            urlsplit(self.control_uss.base_url)
        )
        self.begin_test_step("Validate flight 2 GET interaction")
        # ToDo - Add the test step details
        self.end_test_step()

        self.begin_test_step("Validate flight 1 Notification not sent to Control_uss")
        # ToDo - Add the test step details
        self.end_test_step()

        delete_flight(
            self, "Delete Control_uss flight", self.control_uss_client, self.flight_2_id
        )

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights_fp_client(
            self, (self.control_uss_client, self.tested_uss_client)
        ),
        self.end_cleanup()
