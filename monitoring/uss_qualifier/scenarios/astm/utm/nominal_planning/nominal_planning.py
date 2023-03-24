from typing import Optional

from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    InjectFlightRequest,
    Capability,
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
)
from monitoring.uss_qualifier.scenarios.flight_planning.prioritization_test_steps import (
    plan_conflict_flight_intent,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    clear_area,
    check_capabilities,
    plan_flight_intent,
    cleanup_flights,
    activate_flight_intent,
)


class NominalPlanning(TestScenario):
    first_flight: FlightIntent
    first_flight_id: Optional[str] = None
    first_flight_op_intent_id: Optional[str] = None
    conflicting_flight: FlightIntent
    uss1: FlightPlanner
    uss2: FlightPlanner
    dss: DSSInstance

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        uss1: FlightPlannerResource,
        uss2: FlightPlannerResource,
        dss: DSSInstanceResource,
    ):
        super().__init__()
        self.uss1 = uss1.flight_planner
        self.uss2 = uss2.flight_planner
        self.dss = dss.dss

        flight_intents = flight_intents.get_flight_intents()
        if len(flight_intents) < 2:
            raise ValueError(
                f"`{self.me()}` TestScenario requires at least 2 flight_intents; found {len(flight_intents)}"
            )

        (self.first_flight, self.conflicting_flight) = flight_intents
        if "activated" not in self.first_flight.mutations:
            raise ValueError(
                f"`{self.me()}` TestScenario requires first_flight to have a 'activated' mutation"
            )

    def run(self):
        self.begin_test_scenario()

        self.record_note(
            "First-mover USS",
            f"{self.uss1.config.participant_id}",
        )
        self.record_note(
            "Second USS",
            f"{self.uss2.config.participant_id}",
        )

        self.begin_test_case("Setup")
        if not self._setup():
            return
        self.end_test_case()

        self.begin_test_case("Plan first flight")
        self._plan_first_flight()
        self.end_test_case()

        self.begin_test_case("Attempt second flight")
        self._attempt_second_flight()
        self.end_test_case()

        self.begin_test_case("Activate first flight")
        self._activate_first_flight()
        self.end_test_case()

        self.end_test_scenario()

    def _setup(self) -> bool:
        if not check_capabilities(
            self,
            "Check for necessary capabilities",
            required_capabilities=[
                ([self.uss1, self.uss2], Capability.BasicStrategicConflictDetection)
            ],
        ):
            return False

        clear_area(
            self,
            "Area clearing",
            [self.first_flight, self.conflicting_flight],
            [self.uss1, self.uss2],
        )

        return True

    def _plan_first_flight(self):
        resp, self.first_flight_id = plan_flight_intent(
            self, "Plan flight intent", self.uss1, self.first_flight.request
        )
        self.first_flight_op_intent_id = resp.operational_intent_id

        validate_shared_operational_intent(
            self,
            "Validate flight sharing",
            self.first_flight.request,
            self.first_flight_op_intent_id,
        )

    def _attempt_second_flight(self):
        _ = plan_conflict_flight_intent(
            self,
            "Plan second flight with non-permitted equal priority conflict",
            self.uss2,
            self.conflicting_flight.request,
        )

        # todo: add check flight intent was not planned

    def _activate_first_flight(self):
        first_flight_activated = self.first_flight.get_mutated("activated")
        _ = activate_flight_intent(
            self,
            "Activate first flight",
            self.uss1,
            self.first_flight_id,
            first_flight_activated.request,
        )

        validate_shared_operational_intent(
            self,
            "Validate flight sharing",
            first_flight_activated.request,
            self.first_flight_op_intent_id,
        )

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.uss2, self.uss1))
        self.end_cleanup()
