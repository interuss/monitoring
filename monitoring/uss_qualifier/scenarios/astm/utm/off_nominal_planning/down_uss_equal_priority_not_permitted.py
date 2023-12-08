from typing import Dict

from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    OperationalIntentReference,
)
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightResponseResult,
)

from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntent,
)

from monitoring.uss_qualifier.scenarios.astm.utm import DownUSS
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    OpIntentValidator,
    set_uss_down,
    set_uss_available,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    submit_flight_intent,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class DownUSSEqualPriorityNotPermitted(DownUSS):
    flight2_planned: FlightIntent

    def _parse_flight_intents(self, flight_intents: Dict[str, FlightIntent]) -> None:
        try:
            self.flight2_planned = flight_intents["flight2_planned"]

            assert (
                self.flight2_planned.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight2_planned must have state Accepted"

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

        self.begin_test_case("Setup")
        self._setup()
        self.end_test_case()

        self.begin_test_case(
            "Plan flight in conflict with activated flight managed by down USS"
        )
        oi_ref = self._plan_flight_conflict_activated()
        self.end_test_case()

        self.begin_test_case(
            "Plan flight in conflict with nonconforming flight managed by down USS"
        )
        oi_ref = self._plan_flight_conflict_nonconforming(oi_ref)
        self.end_test_case()

        self.begin_test_case(
            "Plan flight in conflict with contingent flight managed by down USS"
        )
        self._plan_flight_conflict_contingent(oi_ref)
        self.end_test_case()

        self.end_test_scenario()

    def _plan_flight_conflict_activated(self) -> OperationalIntentReference:

        # Virtual USS creates conflicting operational intent test step
        oi_ref = self._put_conflicting_op_intent_step(
            self.flight2_planned, OperationalIntentState.Accepted
        )

        # Virtual USS activates conflicting operational intent test step
        oi_ref = self._put_conflicting_op_intent_step(
            self.flight2_planned, OperationalIntentState.Activated, oi_ref
        )

        # Declare virtual USS as down at DSS test step
        set_uss_down(
            self, "Declare virtual USS as down at DSS", self.dss, self.uss_qualifier_sub
        )

        # Tested USS attempts to plan high-priority flight 2 test step
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate high-priority flight 2 not shared",
            self._intents_extent,
        ) as validator:
            submit_flight_intent(
                self,
                "Tested USS attempts to plan high-priority flight 2",
                "Incorrectly planned",
                {
                    InjectFlightResponseResult.Rejected,
                    InjectFlightResponseResult.ConflictWithFlight,
                },
                {
                    InjectFlightResponseResult.Failed: "Failure",
                },
                self.tested_uss,
                self.flight2_planned.request,
            )
            validator.expect_not_shared()

        # Restore virtual USS availability at DSS test step
        set_uss_available(
            self,
            "Restore virtual USS availability at DSS",
            self.dss,
            self.uss_qualifier_sub,
        )

        return oi_ref

    def _plan_flight_conflict_nonconforming(
        self, oi_ref: OperationalIntentReference
    ) -> OperationalIntentReference:

        # Virtual USS transitions to Nonconforming conflicting operational intent test step
        oi_ref = self._put_conflicting_op_intent_step(
            self.flight2_planned, OperationalIntentState.Nonconforming, oi_ref
        )

        # Declare virtual USS as down at DSS test step
        set_uss_down(
            self, "Declare virtual USS as down at DSS", self.dss, self.uss_qualifier_sub
        )

        # Tested USS attempts to plan high-priority flight 2 test step
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate high-priority flight 2 not shared",
            self._intents_extent,
        ) as validator:
            submit_flight_intent(
                self,
                "Tested USS attempts to plan high-priority flight 2",
                "Incorrectly planned",
                {
                    InjectFlightResponseResult.Rejected,
                    InjectFlightResponseResult.ConflictWithFlight,
                },
                {
                    InjectFlightResponseResult.Failed: "Failure",
                },
                self.tested_uss,
                self.flight2_planned.request,
            )
            validator.expect_not_shared()

        # Restore virtual USS availability at DSS test step
        set_uss_available(
            self,
            "Restore virtual USS availability at DSS",
            self.dss,
            self.uss_qualifier_sub,
        )

        return oi_ref

    def _plan_flight_conflict_contingent(self, oi_ref: OperationalIntentReference):

        # Virtual USS transitions to Contingent conflicting operational intent test step
        self._put_conflicting_op_intent_step(
            self.flight2_planned, OperationalIntentState.Contingent, oi_ref
        )

        # Declare virtual USS as down at DSS test step
        set_uss_down(
            self, "Declare virtual USS as down at DSS", self.dss, self.uss_qualifier_sub
        )

        # Tested USS attempts to plan high-priority flight 2 test step
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate high-priority flight 2 not shared",
            self._intents_extent,
        ) as validator:
            submit_flight_intent(
                self,
                "Tested USS attempts to plan high-priority flight 2",
                "Incorrectly planned",
                {
                    InjectFlightResponseResult.Rejected,
                    InjectFlightResponseResult.ConflictWithFlight,
                },
                {
                    InjectFlightResponseResult.Failed: "Failure",
                },
                self.tested_uss,
                self.flight2_planned.request,
            )
            validator.expect_not_shared()
