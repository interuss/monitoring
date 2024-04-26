from typing import Optional, Tuple

from uas_standards.astm.f3548.v21.api import OperationalIntentState
from uas_standards.interuss.automated_testing.flight_planning.v1.api import (
    BasicFlightPlanInformationUsageState,
    BasicFlightPlanInformationUasState,
)

from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightRequest,
    InjectFlightResponseResult,
    InjectFlightResponse,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlanner,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    submit_flight_intent,
    expect_flight_intent_state,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


def plan_priority_conflict_flight_intent(
    scenario: TestScenarioType,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Attempt to plan a flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in plan_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0015.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_intent,
        BasicFlightPlanInformationUsageState.Planned,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    resp, _, _ = submit_flight_intent(
        scenario,
        "Incorrectly planned",
        {
            InjectFlightResponseResult.ConflictWithFlight,
            InjectFlightResponseResult.Rejected,
        },
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
    )

    return resp


def modify_planned_priority_conflict_flight_intent(
    scenario: TestScenarioType,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
    flight_id: str,
) -> InjectFlightResponse:
    """Attempt to modify a planned flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in modify_planned_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0020.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_intent,
        BasicFlightPlanInformationUsageState.Planned,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    resp, _, _ = submit_flight_intent(
        scenario,
        "Incorrectly modified",
        {
            InjectFlightResponseResult.ConflictWithFlight,
            InjectFlightResponseResult.Rejected,
        },
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )

    return resp


def activate_priority_conflict_flight_intent(
    scenario: TestScenarioType,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
    flight_id: Optional[str] = None,
) -> InjectFlightResponse:
    """Attempt to activate a flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in activate_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0025.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_intent,
        BasicFlightPlanInformationUsageState.InUse,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    resp, _, _ = submit_flight_intent(
        scenario,
        "Incorrectly activated",
        {
            InjectFlightResponseResult.ConflictWithFlight,
            InjectFlightResponseResult.Rejected,
        },
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )

    return resp


def modify_activated_priority_conflict_flight_intent(
    scenario: TestScenarioType,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
    flight_id: str,
) -> InjectFlightResponse:
    """Attempt to modify an activated flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in modify_activated_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0030.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_intent,
        BasicFlightPlanInformationUsageState.InUse,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    resp, _, _ = submit_flight_intent(
        scenario,
        "Incorrectly modified",
        {
            InjectFlightResponseResult.ConflictWithFlight,
            InjectFlightResponseResult.Rejected,
        },
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )

    return resp


def plan_conflict_flight_intent(
    scenario: TestScenarioType,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Attempt to plan a flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in plan_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0035.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_intent,
        BasicFlightPlanInformationUsageState.Planned,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    resp, _, _ = submit_flight_intent(
        scenario,
        "Incorrectly planned",
        {
            InjectFlightResponseResult.ConflictWithFlight,
            InjectFlightResponseResult.Rejected,
        },
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
    )

    return resp


def modify_planned_conflict_flight_intent(
    scenario: TestScenarioType,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
    flight_id: str,
) -> InjectFlightResponse:
    """Attempt to modify a planned flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in modify_planned_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0040.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_intent,
        BasicFlightPlanInformationUsageState.Planned,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    resp, _, _ = submit_flight_intent(
        scenario,
        "Incorrectly modified",
        {
            InjectFlightResponseResult.ConflictWithFlight,
            InjectFlightResponseResult.Rejected,
        },
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )

    return resp


def activate_conflict_flight_intent(
    scenario: TestScenarioType,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
    flight_id: Optional[str] = None,
) -> InjectFlightResponse:
    """Attempt to activate a flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in activate_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0045.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_intent,
        BasicFlightPlanInformationUsageState.InUse,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    resp, _, _ = submit_flight_intent(
        scenario,
        "Incorrectly activated",
        {
            InjectFlightResponseResult.ConflictWithFlight,
            InjectFlightResponseResult.Rejected,
        },
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )

    return resp


def modify_activated_conflict_flight_intent(
    scenario: TestScenarioType,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
    flight_id: str,
) -> InjectFlightResponse:
    """Attempt to modify an activated flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in modify_activated_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0050.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_intent,
        BasicFlightPlanInformationUsageState.InUse,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    resp, _, _ = submit_flight_intent(
        scenario,
        "Incorrectly modified",
        {
            InjectFlightResponseResult.ConflictWithFlight,
            InjectFlightResponseResult.Rejected,
        },
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )

    return resp
