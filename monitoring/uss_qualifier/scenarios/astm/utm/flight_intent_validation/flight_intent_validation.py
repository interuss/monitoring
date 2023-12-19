import arrow

from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.astm.f3548.v21.api import OperationalIntentState
from uas_standards.astm.f3548.v21.constants import OiMaxPlanHorizonDays

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
    plan_flight_intent,
    cleanup_flights,
    submit_flight_intent,
    delete_flight_intent,
)
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightResponseResult,
)


class FlightIntentValidation(TestScenario):

    valid_flight: FlightIntent
    valid_activated: FlightIntent

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
            (
                self.valid_flight,
                self.valid_activated,
                self.invalid_too_far_away,
                self.valid_conflict_tiny_overlap,
            ) = (
                _flight_intents["valid_flight"],
                _flight_intents["valid_activated"],
                _flight_intents["invalid_too_far_away"],
                _flight_intents["valid_conflict_tiny_overlap"],
            )

            now = arrow.utcnow().datetime
            for intent_name, intent in _flight_intents.items():
                if (
                    intent.request.operational_intent.state
                    == OperationalIntentState.Activated
                ):
                    assert Volume4DCollection.from_interuss_scd_api(
                        intent.request.operational_intent.volumes
                        + intent.request.operational_intent.off_nominal_volumes
                    ).has_active_volume(
                        now
                    ), f"at least one volume of activated intent {intent_name} must be active now (now is {now})"

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

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.record_note(
            "Tested USS",
            f"{self.tested_uss.config.participant_id}",
        )

        self.begin_test_case("Attempt to plan invalid flight intents")
        self._attempt_invalid()
        self.end_test_case()

        self.begin_test_case("Validate transition to Ended state after cancellation")
        self._validate_ended_cancellation()
        self.end_test_case()

        self.begin_test_case("Validate precision of intersection computations")
        self._validate_precision_intersection()
        self.end_test_case()

        self.end_test_scenario()

    def _attempt_invalid(self):
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate flight intent too far ahead of time not planned",
            self._intents_extent,
        ) as validator:
            self.begin_test_step("Attempt to plan flight intent too far ahead of time")
            submit_flight_intent(
                self,
                "Incorrectly planned",
                {InjectFlightResponseResult.Rejected},
                {InjectFlightResponseResult.Failed: "Failure"},
                self.tested_uss,
                self.invalid_too_far_away.request,
            )
            self.end_test_step()

            validator.expect_not_shared()

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
                self.begin_test_step("Plan flight intent")
                _, flight_id, _ = plan_flight_intent(
                    self,
                    self.tested_uss,
                    self.valid_flight.request,
                )
                self.end_test_step()
                planned_validator.expect_shared(self.valid_flight.request)

            _ = delete_flight_intent(
                self, "Cancel flight intent", self.tested_uss, flight_id
            )
            cancelled_validator.expect_not_shared()

    def _validate_precision_intersection(self):
        self.begin_test_step("Plan control flight intent")
        _, _, _ = plan_flight_intent(
            self,
            self.tested_uss,
            self.valid_flight.request,
        )
        self.end_test_step()

        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate conflicting flight not planned",
            self._intents_extent,
        ) as validator:
            self.begin_test_step("Attempt to plan flight conflicting by a tiny overlap")
            submit_flight_intent(
                self,
                "Incorrectly planned",
                {
                    InjectFlightResponseResult.ConflictWithFlight,
                    InjectFlightResponseResult.Rejected,
                },
                {InjectFlightResponseResult.Failed: "Failure"},
                self.tested_uss,
                self.valid_conflict_tiny_overlap.request,
            )
            self.end_test_step()

            validator.expect_not_shared()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, [self.tested_uss])
        self.end_cleanup()
