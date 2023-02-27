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
    activate_priority_conflict_flight_intent,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    clear_area,
    check_capabilities,
    inject_successful_flight_intent,
    cleanup_flights,
    activate_valid_flight_intent,
)


class NominalPlanningPriority(TestScenario):
    first_flight: InjectFlightRequest
    first_flight_activated: InjectFlightRequest
    first_flight_id: Optional[str]
    priority_flight: InjectFlightRequest
    priority_flight_activated: InjectFlightRequest
    priority_flight_id: Optional[str]
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

        flight_intents = flight_intents.get_flight_intents()
        if len(flight_intents) < 4:
            raise ValueError(
                f"`{self.me()}` TestScenario requires at least 4 flight_intents; found {len(flight_intents)}"
            )
        (
            self.first_flight,
            self.first_flight_activated,
            self.priority_flight,
            self.priority_flight_activated,
        ) = flight_intents
        if (
            self.priority_flight.operational_intent.priority
            <= self.first_flight.operational_intent.priority
            or self.priority_flight_activated.operational_intent.priority
            <= self.first_flight.operational_intent.priority
        ):
            raise ValueError(
                f"`{self.me()}` TestScenario requires the second and third flight_intent to be higher priority than the first flight_intent; instead found priorities {self.first_flight.operational_intent.priority} then {self.priority_flight.operational_intent.priority} and {self.priority_flight_activated.operational_intent.priority}"
            )
        elif (
            self.priority_flight.operational_intent.priority
            != self.priority_flight_activated.operational_intent.priority
        ):
            raise ValueError(
                f"`{self.me()}` TestScenario requires the second flight_intent to the same priority as the third flight_intent; instead found priorities {self.priority_flight.operational_intent.priority} and {self.priority_flight_activated.operational_intent.priority}"
            )
        self.first_flight_id, self.priority_flight_id = None, None

        self.dss = dss.dss

    def run(self):
        self.begin_test_scenario()

        self.record_note(
            "First USS",
            f"{self.uss1.config.participant_id}",
        )
        self.record_note(
            "Priority USS",
            f"{self.uss2.config.participant_id}",
        )

        self.begin_test_case("Setup")
        if not self._setup():
            return
        self.end_test_case()

        self.begin_test_case("Plan first flight")
        self._plan_first_flight()
        self.end_test_case()

        self.begin_test_case("Plan priority flight")
        self._plan_priority_flight()
        self.end_test_case()

        self.begin_test_case("Activate priority flight")
        self._activate_priority_flight()
        self.end_test_case()

        self.begin_test_case("Attempt to activate first flight")
        self._activate_first_flight_attempt()
        self.end_test_case()

        self.end_test_scenario()

    def _setup(self) -> bool:
        if not check_capabilities(
            self,
            "Check for necessary capabilities",
            required_capabilities=[
                ([self.uss1, self.uss2], Capability.BasicStrategicConflictDetection)
            ],
            prerequisite_capabilities=[(self.uss2, Capability.HighPriorityFlights)],
        ):
            return False

        clear_area(
            self,
            "Area clearing",
            [self.first_flight, self.priority_flight, self.priority_flight_activated],
            [self.uss1, self.uss2],
        )

        return True

    def _plan_first_flight(self):
        resp, self.first_flight_id = inject_successful_flight_intent(
            self, "Inject flight intent", self.uss1, self.first_flight
        )

        validate_shared_operational_intent(
            self,
            "Validate flight sharing",
            self.first_flight,
            resp.operational_intent_id,
        )

    def _plan_priority_flight(self):
        resp, self.priority_flight_id = inject_successful_flight_intent(
            self, "Inject flight intent", self.uss2, self.priority_flight
        )

        validate_shared_operational_intent(
            self,
            "Validate flight sharing",
            self.priority_flight,
            resp.operational_intent_id,
        )

    def _activate_priority_flight(self):
        resp = activate_valid_flight_intent(
            self,
            "Activate priority flight",
            self.uss2,
            self.priority_flight_id,
            self.priority_flight_activated,
        )

        validate_shared_operational_intent(
            self,
            "Validate flight sharing",
            self.priority_flight_activated,
            resp.operational_intent_id,
        )

    def _activate_first_flight_attempt(self):
        resp = activate_priority_conflict_flight_intent(
            self,
            "Activate first flight with higher priority conflict",
            self.uss1,
            self.first_flight_id,
            self.first_flight_activated,
        )

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.uss2, self.uss1))
        self.end_cleanup()
