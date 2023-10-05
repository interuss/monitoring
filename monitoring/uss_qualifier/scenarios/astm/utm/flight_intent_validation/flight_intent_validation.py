from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.uss_qualifier.common_data_definitions import Severity
from uas_standards.astm.f3548.v21.api import OperationalIntentState
from uas_standards.astm.f3548.v21.constants import OiMaxPlanHorizonDays
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
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    clear_area,
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

    valid_conflict_tiny_overlap: FlightIntent

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

        extents = []
        for intent in flight_intents.values():
            extents.extend(intent.request.operational_intent.volumes)
            extents.extend(intent.request.operational_intent.off_nominal_volumes)
        self._intents_extent = Volume4DCollection.from_interuss_scd_api(
            extents
        ).bounding_volume.to_f3548v21()

        try:
            (
                self.valid_flight,
                self.valid_activated,
                self.invalid_too_far_away,
                self.invalid_accepted_offnominal,
                self.invalid_activated_offnominal,
                self.valid_conflict_tiny_overlap,
            ) = (
                flight_intents["valid_flight"],
                flight_intents["valid_activated"],
                flight_intents["invalid_too_far_away"],
                flight_intents["invalid_accepted_offnominal"],
                flight_intents["invalid_activated_offnominal"],
                flight_intents["valid_conflict_tiny_overlap"],
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
            assert (
                self.valid_conflict_tiny_overlap.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "valid_conflict_tiny_overlap must have state Accepted"

            time_delta = (
                Volume4DCollection.from_interuss_scd_api(
                    self.invalid_too_far_away.request.operational_intent.volumes
                ).time_start.datetime
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

            assert Volume4DCollection.from_interuss_scd_api(
                self.valid_flight.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_interuss_scd_api(
                    self.valid_conflict_tiny_overlap.request.operational_intent.volumes
                )
            ), "valid_flight and valid_conflict_tiny_overlap must intersect"

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

        self.begin_test_case("Validate precision of intersection computations")
        self._validate_precision_intersection()
        self.end_test_case()

        self.end_test_scenario()

    def _setup(self) -> bool:
        self.begin_test_step("Check for flight planning readiness")

        error, query = self.tested_uss.get_readiness()
        self.record_query(query)
        with self.check(
            "Flight planning USS not ready", [self.tested_uss.participant_id]
        ) as check:
            if error:
                check.record_failed(
                    "Error determining readiness",
                    Severity.High,
                    "Error: " + error,
                    query_timestamps=[query.request.timestamp],
                )

        self.end_test_step()

        clear_area(
            self,
            "Area clearing",
            [
                self.valid_flight,
                self.valid_activated,
                self.invalid_accepted_offnominal,
                self.invalid_activated_offnominal,
                self.invalid_too_far_away,
                self.valid_conflict_tiny_overlap,
            ],
            [self.tested_uss],
        )

        return True

    def _attempt_invalid(self):
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight intent too far ahead of time not planned",
            self._intents_extent,
        ) as validator:
            submit_flight_intent(
                self,
                "Attempt to plan flight intent too far ahead of time",
                "Incorrectly planned",
                {InjectFlightResponseResult.Rejected},
                {InjectFlightResponseResult.Failed: "Failure"},
                self.tested_uss,
                self.invalid_too_far_away.request,
            )
            validator.expect_not_shared()

    def _attempt_invalid_offnominal(self):
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight intent with an off-nominal volume not planned",
            self._intents_extent,
        ) as validator:
            submit_flight_intent(
                self,
                "Attempt to plan flight with an off-nominal volume",
                "Incorrectly planned",
                {InjectFlightResponseResult.Rejected},
                {InjectFlightResponseResult.Failed: "Failure"},
                self.tested_uss,
                self.invalid_accepted_offnominal.request,
            )
            validator.expect_not_shared()

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight sharing",
            self._intents_extent,
        ) as validator:
            _, valid_flight_id = plan_flight_intent(
                self,
                "Plan valid flight intent",
                self.tested_uss,
                self.valid_flight.request,
            )
            valid_flight_op_intent_ref = validator.expect_shared(
                self.valid_flight.request
            )

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate planned flight not modified",
            self._intents_extent,
            valid_flight_op_intent_ref,
        ) as validator:
            submit_flight_intent(
                self,
                "Attempt to modify planned flight with an off-nominal volume",
                "Incorrectly modified",
                {InjectFlightResponseResult.Rejected},
                {InjectFlightResponseResult.Failed: "Failure"},
                self.tested_uss,
                self.invalid_accepted_offnominal.request,
            )
            valid_flight_op_intent_ref = validator.expect_shared(
                self.valid_flight.request
            )

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight sharing",
            self._intents_extent,
            valid_flight_op_intent_ref,
        ) as validator:
            activate_flight_intent(
                self,
                "Activate valid flight intent",
                self.tested_uss,
                self.valid_activated.request,
                valid_flight_id,
            )
            valid_flight_op_intent_ref = validator.expect_shared(
                self.valid_activated.request
            )

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate activated flight not modified",
            self._intents_extent,
            valid_flight_op_intent_ref,
        ) as validator:
            submit_flight_intent(
                self,
                "Attempt to modify activated flight with an off-nominal volume",
                "Incorrectly modified",
                {InjectFlightResponseResult.Rejected},
                {InjectFlightResponseResult.Failed: "Failure"},
                self.tested_uss,
                self.invalid_activated_offnominal.request,
            )
            validator.expect_shared(self.valid_flight.request)

        _ = delete_flight_intent(
            self, "Delete valid flight intent", self.tested_uss, valid_flight_id
        )

    def _validate_ended_cancellation(self):
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight intent is non-discoverable",
            self._intents_extent,
        ) as cancelled_validator:
            with OpIntentValidator(
                self,
                self.tested_uss,
                self.dss,
                "Validate flight intent shared correctly",
                self._intents_extent,
            ) as planned_validator:
                _, flight_id = plan_flight_intent(
                    self,
                    "Plan flight intent",
                    self.tested_uss,
                    self.valid_flight.request,
                )
                planned_validator.expect_shared(self.valid_flight.request)

            _ = delete_flight_intent(
                self, "Cancel flight intent", self.tested_uss, flight_id
            )
            cancelled_validator.expect_not_shared()

    def _validate_precision_intersection(self):
        _, _ = plan_flight_intent(
            self,
            "Plan control flight intent",
            self.tested_uss,
            self.valid_flight.request,
        )

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate conflicting flight not planned",
            self._intents_extent,
        ) as validator:
            submit_flight_intent(
                self,
                "Attempt to plan flight conflicting by a tiny overlap",
                "Incorrectly planned",
                {InjectFlightResponseResult.ConflictWithFlight},
                {InjectFlightResponseResult.Failed: "Failure"},
                self.tested_uss,
                self.valid_conflict_tiny_overlap.request,
            )
            validator.expect_not_shared()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, [self.tested_uss])
        self.end_cleanup()
