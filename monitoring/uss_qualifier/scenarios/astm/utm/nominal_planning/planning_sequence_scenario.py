from abc import ABC, abstractmethod

from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
    FlightPlannerResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentID,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    estimate_scenario_execution_max_extents,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.scenarios.astm.utm.clear_area_validation import (
    validate_clear_area,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    cleanup_flights,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class PlanningSequenceScenario(TestScenario, ABC):
    """Abstracts a test scenario where a sequence of planning actions are performed.

    The provided flight_intents will be validated against expected_flight_intents and the flight intent templates
    extracted from flight_intents will be added as attributes to this scenario object according to their intent_ids.
    """

    tested_uss: FlightPlannerClient
    control_uss: FlightPlannerClient
    dss: DSSInstance
    flight_intents_templates: dict[FlightIntentID, FlightInfoTemplate]
    # Note: FlightInfoTemplate attributes named according to flight_intents' intent_ids will also be present

    def __init__(
        self,
        tested_uss: FlightPlannerResource,
        control_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
        flight_intents: FlightIntentsResource,
        expected_flight_intents: list[ExpectedFlightIntent],
        scopes: dict[Scope, str],
    ):
        super().__init__()
        self.tested_uss = tested_uss.client
        self.control_uss = control_uss.client
        self.dss = dss.get_instance({k.value: v for k, v in scopes.items()})

        self.flight_intents_templates = flight_intents.get_flight_intents()
        try:
            validate_flight_intent_templates(
                self.flight_intents_templates, expected_flight_intents
            )
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

        for efi in expected_flight_intents:
            setattr(self, efi.intent_id, self.flight_intents_templates[efi.intent_id])

        self.flight_intents_templates = (
            flight_intents.get_flight_intents() if flight_intents else {}
        )
        try:
            validate_flight_intent_templates(
                self.flight_intents_templates, expected_flight_intents
            )
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

    def resolve_flight(self, flight_template: FlightInfoTemplate) -> FlightInfo:
        return flight_template.resolve(self.time_context.evaluate_now())

    @abstractmethod
    def run_planning_sequence(self, context: ExecutionContext):
        """Run the main planning sequence of the test scenario, assuming the test scenario has already begun."""
        raise NotImplementedError()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.record_note(
            "Tested USS",
            f"{self.tested_uss.participant_id}",
        )
        self.record_note(
            "Control USS",
            f"{self.control_uss.participant_id}",
        )

        self.begin_test_case("Prerequisites check")
        self.begin_test_step("Verify area is clear")
        estimated_max_extents = estimate_scenario_execution_max_extents(
            self.time_context, self.flight_intents_templates
        )
        validate_clear_area(
            self,
            self.dss,
            [estimated_max_extents],
            ignore_self=False,
        )
        self.end_test_step()
        self.end_test_case()

        self.run_planning_sequence(context)

        self.end_test_scenario()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.control_uss, self.tested_uss))
        self.end_cleanup()
