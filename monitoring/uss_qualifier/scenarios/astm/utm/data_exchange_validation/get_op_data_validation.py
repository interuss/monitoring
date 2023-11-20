from typing import Optional, Dict

from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.temporal import TimeDuringTest, Time
import arrow

from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
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
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import OpIntentValidator

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


class GetOpResponseDataValidationByUSS(TestScenario):
    flight_1: FlightInfoTemplate
    flight_2: FlightInfoTemplate

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
            msg = f"No FlightIntentsResource was provided as input to this test, it is assumed that the jurisdiction does not allow any same priority conflicts, execution of the scenario was stopped without failure"
            self.record_note(
                "Jurisdiction of tested USS does not allow any same priority conflicts",
                msg,
            )
            raise ScenarioCannotContinueError(msg)

        _flight_intents = flight_intents.get_flight_intents()

        t_now = Time(arrow.utcnow().datetime)
        times = {
            TimeDuringTest.StartOfTestRun: t_now,
            TimeDuringTest.StartOfScenario: t_now,
            TimeDuringTest.TimeOfEvaluation: t_now,
        }
        extents = []
        for intent in _flight_intents.values():
            extents.append(intent.resolve(times).basic_information.area.bounding_volume)
        self._intents_extent = Volume4DCollection(extents).bounding_volume.to_f3548v21()

        try:
            (self.flight_1, self.flight_2,) = (
                _flight_intents["flight_1"],
                _flight_intents["flight_2"],
            )

            assert not self.flight_1.resolve(
                times
            ).basic_information.area.intersects_vol4s(
                self.flight_2.resolve(times).basic_information.area
            ), "flight_1 and flight_2 must not intersect"

        except KeyError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: missing flight intent {e}"
            )
        except AssertionError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

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
            f"{self.control_uss_client.participant_id}",
        )

        self.begin_test_case("Successfully plan flight near an existing flight")
        self._tested_uss_plans_deconflicted_flight_near_existing_flight(times)
        self.end_test_case()

        self.begin_test_case("Flight planning prevented due to invalid data sharing")
        self._tested_uss_unable_to_plan_flight_near_invalid_shared_existing_flight(
            times
        )
        self.end_test_case()

        self.end_test_scenario()

    def _tested_uss_plans_deconflicted_flight_near_existing_flight(
        self, times: Dict[TimeDuringTest, Time]
    ):
        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        flight_2 = self.flight_2.resolve(times)
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
                flight_2,
            )

            validator.expect_shared(flight_2)

        self.begin_test_step(
            "Precondition - check tested_uss has no subscription in flight 2 area"
        )
        # ToDo - Add the test step details
        self.end_test_step()

        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        flight_1 = self.flight_1.resolve(times)

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
                flight_1,
            )

            validator.expect_shared(
                flight_1,
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

    def _tested_uss_unable_to_plan_flight_near_invalid_shared_existing_flight(
        self, times: Dict[TimeDuringTest, Time]
    ):
        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        flight_info = self.flight_2.resolve(times)

        # Modifying the request with invalid data
        behavior = MockUssFlightBehavior(
            modify_sharing_methods=["GET", "POST"],
            modify_fields={
                "reference": {"state": "Flying"},
                "details": {"priority": -1},
            },
        )

        additional_fields = {"behavior": behavior}

        _, self.flight_2_id = plan_flight(
            self,
            "Control_uss plans flight 2, sharing invalid operational intent data",
            self.control_uss_client,
            flight_info,
            additional_fields,
        )

        self.begin_test_step(
            "Validate flight 2 shared operational intent with invalid data"
        )
        # ToDo - Add the test step details
        self.end_test_step()

        self.begin_test_step(
            "Precondition - check tested_uss has no subscription in flight 2 area"
        )
        # ToDo - Add the test step details
        self.end_test_step()

        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        flight_1 = self.flight_1.resolve(times)

        _, self.flight_1_id = plan_flight_intent_expect_failed(
            self,
            "Tested_uss attempts to plan flight 1, expect failure",
            self.tested_uss_client,
            flight_1,
        )

        self.begin_test_step("Validate flight 1 not shared by tested_uss")
        # ToDo - Add the test step details
        self.end_test_step()

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
