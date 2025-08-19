from uas_standards.astm.f3548.v21.api import OperationalIntentReference
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
    FlightPlannersResource,
)
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSResource
from monitoring.uss_qualifier.scenarios.astm.utm.clear_area_validation import (
    validate_clear_area,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.test_step_fragments import (
    remove_op_intent,
)
from monitoring.uss_qualifier.scenarios.flight_planning.prep_planners import (
    PrepareFlightPlannersScenario,
)


class PrepareFlightPlanners(PrepareFlightPlannersScenario):
    dss: DSSInstance

    def __init__(
        self,
        flight_planners: FlightPlannersResource,
        dss: DSSInstanceResource,
        flight_intents: FlightIntentsResource,
        mock_uss: MockUSSResource | None = None,
        flight_intents2: FlightIntentsResource | None = None,
        flight_intents3: FlightIntentsResource | None = None,
        flight_intents4: FlightIntentsResource | None = None,
    ):
        super().__init__(
            flight_planners,
            flight_intents,
            mock_uss,
            flight_intents2,
            flight_intents3,
            flight_intents4,
        )
        self.dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "search for operational intent references and remove ones under uss_qualifier management"
            }
        )

    def run(self, context):
        self.begin_test_scenario(context)

        self.begin_test_case("Flight planners preparation")

        self.begin_test_step("Check for flight planning readiness")
        self._check_readiness()
        self.end_test_step()

        self.begin_test_step("Area clearing")
        self._clear_area()
        self.end_test_step()

        self.begin_test_step("Clear area validation")
        remaining_op_intents = validate_clear_area(
            self,
            self.dss,
            self.areas,
            ignore_self=True,
        )
        self.end_test_step()

        self.end_test_case()

        if remaining_op_intents:
            self.begin_test_case("uss_qualifier preparation")

            self.begin_test_step("Remove uss_qualifier op intents")
            self._remove_my_op_intents(remaining_op_intents)
            self.end_test_step()

            self.begin_test_step("Clear area validation")
            validate_clear_area(self, self.dss, self.areas, ignore_self=False)
            self.end_test_step()

            self.end_test_case()

        self.end_test_scenario()

    def _remove_my_op_intents(
        self, my_op_intents: list[OperationalIntentReference]
    ) -> None:
        already_removed = set()
        for oi_ref in my_op_intents:
            if oi_ref.id in already_removed:
                continue
            remove_op_intent(self, self.dss, oi_ref.id, oi_ref.ovn)
            already_removed.add(oi_ref.id)
