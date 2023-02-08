from typing import Optional

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    InjectFlightRequest,
    InjectFlightResult,
    Capability,
)
from monitoring.uss_qualifier.common_data_definitions import Severity
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
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    clear_area,
    check_capabilities,
    inject_successful_flight_intent,
    cleanup_flights,
    activate_valid_flight_intent,
)


class NominalPlanning(TestScenario):
    first_flight: InjectFlightRequest
    first_flight_id: Optional[str]
    conflicting_flight: InjectFlightRequest
    first_flight_activated: InjectFlightRequest
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
        if len(flight_intents) < 3:
            raise ValueError(
                f"`{self.me()}` TestScenario requires at least 3 flight_intents; found {len(flight_intents)}"
            )
        (
            self.first_flight,
            self.conflicting_flight,
            self.first_flight_activated,
        ) = flight_intents
        self.first_flight_id = None

        self.dss = dss.dss

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
        if not self._plan_first_flight():
            return
        self.end_test_case()

        self.begin_test_case("Attempt second flight")
        if not self._attempt_second_flight():
            return
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
            [self.first_flight, self.conflicting_flight, self.first_flight_activated],
            [self.uss1, self.uss2],
        )

        return True

    def _plan_first_flight(self) -> bool:
        resp, flight_id = inject_successful_flight_intent(
            self, "Inject flight intent", self.uss1, self.first_flight
        )
        if resp is None:
            return False
        self.first_flight_id = flight_id
        op_intent_id = resp.operational_intent_id

        validate_shared_operational_intent(
            self, "Validate flight sharing", self.first_flight, op_intent_id
        )

        return True

    def _attempt_second_flight(self) -> bool:
        self.begin_test_step("Inject flight intent")

        with self.check("Incorrectly planned", [self.uss2.participant_id]) as check:
            try:
                resp, query, flight_id = self.uss2.request_flight(
                    self.conflicting_flight
                )
            except QueryError as e:
                for q in e.queries:
                    self.record_query(q)
                check.record_failed(
                    summary=f"Error from {self.uss2.participant_id} when attempting second flight",
                    severity=Severity.High,
                    details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                    query_timestamps=[q.request.timestamp for q in e.queries],
                )
            self.record_query(query)
            if resp.result == InjectFlightResult.Planned:
                check.record_failed(
                    summary="Flight created even though there was a conflict",
                    severity=Severity.High,
                    details="The user's intended flight conflicts with an existing operational intent so the result of attempting to fulfill this flight intent should not be a successful planning of the flight.",
                    query_timestamps=[query.request.timestamp],
                )
                return False
        with self.check("Failure", [self.uss2.participant_id]) as check:
            if resp.result == InjectFlightResult.Failed:
                check.record_failed(
                    summary="Failed to create flight",
                    severity=Severity.High,
                    details=f'{self.uss1.participant_id} Failed to process the user flight intent: "{resp.notes}"',
                    query_timestamps=[query.request.timestamp],
                )
                return False

        self.end_test_step()  # Inject flight intent
        return True

    def _activate_first_flight(self):
        resp = activate_valid_flight_intent(
            self,
            "Activate first flight",
            self.uss1,
            self.first_flight_id,
            self.first_flight_activated,
        )
        if resp is None:
            raise RuntimeError(
                "Flight intent not activated successfully, but a High Severity issue didn't stop scenario execution"
            )
        op_intent_id = resp.operational_intent_id

        validate_shared_operational_intent(
            self, "Validate flight sharing", self.first_flight_activated, op_intent_id
        )

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.uss2, self.uss1))
        self.end_cleanup()
