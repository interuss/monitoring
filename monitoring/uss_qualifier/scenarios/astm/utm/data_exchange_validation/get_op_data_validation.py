from typing import Optional
from loguru import logger

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

from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
)

from monitoring.uss_qualifier.resources.interuss.mock_uss.client import (
    MockUSSClient,
    MockUSSResource,
)


class GetOpResponseDataValidationByUSS(TestScenario):
    flight_1: FlightIntent

    flight_2: FlightIntent

    tested_uss: FlightPlanner
    control_uss: MockUSSClient
    dss: DSSInstance

    def __init__(
        self,
        tested_uss: FlightPlannerResource,
        control_uss: MockUSSResource,
        dss: DSSInstanceResource,
        flight_intents: Optional[FlightIntentsResource] = None,
    ):
        super().__init__()
        self.tested_uss = tested_uss.flight_planner
        self.control_uss = control_uss.mock_uss
        self.dss = dss.dss

    def run(self, context):
        self.begin_test_scenario()
        pass
        self.end_test_scenario()

    def cleanup(self):
        self.begin_cleanup()
        pass
        self.end_cleanup()
