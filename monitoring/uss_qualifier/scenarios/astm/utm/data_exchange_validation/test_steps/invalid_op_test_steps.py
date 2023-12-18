from typing import Optional, Tuple
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlannerClient,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    submit_flight,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.clients.flight_planning.planning import (
    PlanningActivityResponse,
    PlanningActivityResult,
    FlightPlanStatus,
)


def plan_flight_intent_expect_failed(
    scenario: TestScenarioType,
    flight_planner: FlightPlannerClient,
    flight_intent: FlightInfo,
) -> Tuple[PlanningActivityResponse, Optional[str]]:
    """Attempt to plan a flight intent that would result in a Failed result.

    This function implements the test step described in scd_data_exchange_validation.md.
    It validates requirement astm.f3548.v21.SCD00abc.

    Returns: The injection response.
    """

    return submit_flight(
        scenario,
        "Plan should fail",
        {(PlanningActivityResult.Failed, FlightPlanStatus.NotPlanned)},
        {},
        flight_planner,
        flight_intent,
    )
