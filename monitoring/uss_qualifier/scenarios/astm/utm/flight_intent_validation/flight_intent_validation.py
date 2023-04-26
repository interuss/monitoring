from uas_standards.astm.f3548.v21.api import OperationalIntentState
from uas_standards.astm.f3548.v21.constants import OiMaxVertices, OiMaxPlanHorizonDays

from monitoring.monitorlib import scd
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    Capability,
    InjectFlightResult,
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
    validate_shared_operational_intent,
    ValidateNotSharedOperationalIntent,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    clear_area,
    check_capabilities,
    plan_flight_intent,
    cleanup_flights,
    activate_flight_intent,
    submit_flight_intent,
    delete_flight_intent,
)


class FlightIntentValidation(TestScenario):

    valid_flight: FlightIntent
    valid_activated: FlightIntent

    invalid_accepted_offnominal: FlightIntent
    invalid_activated_offnominal: FlightIntent

    invalid_too_far_away: FlightIntent

    # TODO: add the following intents for next tests
    #  valid_conflict_tiny_overlap: FlightIntent

    tested_uss: FlightPlanner
    dss: DSSInstance

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        tested_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
    ):
        super().__init__()
        self.tested_uss = tested_uss.flight_planner
        self.dss = dss.dss

        flight_intents = flight_intents.get_flight_intents()
        try:
            (
                self.valid_flight,
                self.valid_activated,
                self.invalid_too_far_away,
                self.invalid_accepted_offnominal,
                self.invalid_activated_offnominal,
                # TODO: add the following intents for next tests
                #  self.valid_conflict_tiny_overlap,
            ) = (
                flight_intents["valid_flight"],
                flight_intents["valid_activated"],
                flight_intents["invalid_too_far_away"],
                flight_intents["invalid_accepted_offnominal"],
                flight_intents["invalid_activated_offnominal"],
                # TODO: add the following intents for next tests
                #  flight_intents["valid_conflict_tiny_overlap"],
            )

            assert (
                self.valid_flight.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "valid_flight must have state Accepted"
            assert (
                self.valid_activated.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "valid_activated must have state Activated"
            assert (
                self.invalid_too_far_away.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "invalid_too_far_away must have state Accepted"
            assert (
                self.invalid_accepted_offnominal.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "invalid_accepted_offnominal must have state Accepted"
            assert (
                self.invalid_activated_offnominal.request.operational_intent.state
                == OperationalIntentState.Activated
            ), "invalid_activated_offnominal must have state Activated"

            time_delta = (
                scd.start_of(
                    self.invalid_too_far_away.request.operational_intent.volumes
                )
                - self.invalid_too_far_away.reference_time.datetime
            )
            assert (
                time_delta.days > OiMaxPlanHorizonDays
            ), f"invalid_too_far_away must have start time more than {OiMaxPlanHorizonDays} days ahead of reference time, got {time_delta}"

            assert (
                len(
                    self.invalid_accepted_offnominal.request.operational_intent.off_nominal_volumes
                )
                > 0
            ), "invalid_accepted_offnominal must have at least one off-nominal volume"
            assert (
                len(
                    self.invalid_activated_offnominal.request.operational_intent.off_nominal_volumes
                )
                > 0
            ), "invalid_activated_offnominal must have at least one off-nominal volume"

        except KeyError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: missing flight intent {e}"
            )
        except AssertionError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

    def run(self):
        self.begin_test_scenario()
        self.record_note(
            "Tested USS",
            f"{self.tested_uss.config.participant_id}",
        )

        self.begin_test_case("Setup")
        if not self._setup():
            return
        self.end_test_case()

        self.begin_test_case("Attempt to plan invalid flight intents")
        self._attempt_invalid()
        self.end_test_case()

        self.begin_test_case(
            "Attempt to specify off-nominal volume in Accepted and Activated states"
        )
        self._attempt_invalid_offnominal()
        self.end_test_case()

        self.begin_test_case("Validate transition to Ended state after cancellation")
        self._validate_ended_cancellation()
        self.end_test_case()

        self.end_test_scenario()

    def _setup(self) -> bool:
        if not check_capabilities(
            self,
            "Check for necessary capabilities",
            required_capabilities=[
                ([self.tested_uss], Capability.BasicStrategicConflictDetection)
            ],
        ):
            return False

        clear_area(
            self,
            "Area clearing",
            [
                self.valid_flight,
                self.valid_activated,
                self.invalid_accepted_offnominal,
                self.invalid_activated_offnominal,
                self.invalid_too_far_away,
                # TODO: add the following intents for next tests
                #  self.valid_conflict_tiny_overlap,
            ],
            [self.tested_uss],
        )

        return True

    def _attempt_invalid(self):
        with ValidateNotSharedOperationalIntent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight intent too far ahead of time not planned",
            self.invalid_too_far_away.request,
        ):
            resp, _ = submit_flight_intent(
                self,
                "Attempt to plan flight intent too far ahead of time",
                "Incorrectly planned",
                {InjectFlightResult.Rejected},
                {InjectFlightResult.Failed: "Failure"},
                self.tested_uss,
                self.invalid_too_far_away.request,
            )

    def _attempt_invalid_offnominal(self):
        with ValidateNotSharedOperationalIntent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight intent with an off-nominal volume not planned",
            self.invalid_accepted_offnominal.request,
        ):
            resp, _ = submit_flight_intent(
                self,
                "Attempt to plan flight with an off-nominal volume",
                "Incorrectly planned",
                {InjectFlightResult.Rejected},
                {InjectFlightResult.Failed: "Failure"},
                self.tested_uss,
                self.invalid_accepted_offnominal.request,
            )

        resp, valid_flight_id = plan_flight_intent(
            self, "Plan valid flight intent", self.tested_uss, self.valid_flight.request
        )
        valid_flight_op_intent_id = resp.operational_intent_id

        resp, _ = submit_flight_intent(
            self,
            "Attempt to modify planned flight with an off-nominal volume",
            "Incorrectly modified",
            {InjectFlightResult.Rejected},
            {InjectFlightResult.Failed: "Failure"},
            self.tested_uss,
            self.invalid_accepted_offnominal.request,
        )
        validate_shared_operational_intent(
            self,
            self.tested_uss,
            self.dss,
            "Validate planned flight not modified",
            self.valid_flight.request,
            valid_flight_op_intent_id,
        )

        resp = activate_flight_intent(
            self,
            "Activate valid flight intent",
            self.tested_uss,
            valid_flight_id,
            self.valid_activated.request,
        )
        valid_flight_op_intent_id = resp.operational_intent_id

        resp, _ = submit_flight_intent(
            self,
            "Attempt to modify activated flight with an off-nominal volume",
            "Incorrectly modified",
            {InjectFlightResult.Rejected},
            {InjectFlightResult.Failed: "Failure"},
            self.tested_uss,
            self.invalid_activated_offnominal.request,
        )
        validate_shared_operational_intent(
            self,
            self.tested_uss,
            self.dss,
            "Validate activated flight not modified",
            self.valid_activated.request,
            valid_flight_op_intent_id,
        )

        _ = delete_flight_intent(
            self, "Delete valid flight intent", self.tested_uss, valid_flight_id
        )

    def _validate_ended_cancellation(self):
        with ValidateNotSharedOperationalIntent(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight intent is non-discoverable",
            self.valid_flight.request,
        ):
            resp, flight_id = plan_flight_intent(
                self, "Plan flight intent", self.tested_uss, self.valid_flight.request
            )
            validate_shared_operational_intent(
                self,
                self.tested_uss,
                self.dss,
                "Validate flight intent shared correctly",
                self.valid_flight.request,
                resp.operational_intent_id,
            )

            _ = delete_flight_intent(
                self, "Cancel flight intent", self.tested_uss, flight_id
            )

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, [self.tested_uss])
        self.end_cleanup()
