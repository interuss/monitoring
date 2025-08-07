import arrow
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import FlightIntentsResource
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerResource,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    cleanup_flights,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class SoloHappyPath(TestScenario):
    times: dict[TimeDuringTest, Time]

    flight1_id: str | None = None
    flight1_planned: FlightInfoTemplate
    flight1_activated: FlightInfoTemplate

    tested_uss: FlightPlannerClient
    dss: DSSInstance

    def __init__(
        self,
        tested_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
        flight_intents: FlightIntentsResource | None = None,
    ):
        super().__init__()
        self.tested_uss = tested_uss.client

        scopes = {
            Scope.StrategicCoordination: "search for operational intent references to verify outcomes of planning activities and retrieve operational intent details"
        }

        self.dss = dss.get_instance(scopes)

        expected_flight_intents = [
            ExpectedFlightIntent(
                "flight1_planned",
                "Flight",
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight1_activated",
                "Flight",
                usage_state=AirspaceUsageState.InUse,
                uas_state=UasState.Nominal,
            ),
        ]

        templates = flight_intents.get_flight_intents()
        try:
            self._intents_extent = validate_flight_intent_templates(
                templates, expected_flight_intents
            )
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

        for efi in expected_flight_intents:
            setattr(self, efi.intent_id, templates[efi.intent_id])

    def run(self, context: ExecutionContext):
        self.times = {
            TimeDuringTest.StartOfTestRun: Time(context.start_time),
            TimeDuringTest.StartOfScenario: Time(arrow.utcnow().datetime),
        }

        self.begin_test_scenario(context)

        # TODO(#751): Implement scenario

        self.end_test_scenario()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, (self.tested_uss,))
        self.end_cleanup()
