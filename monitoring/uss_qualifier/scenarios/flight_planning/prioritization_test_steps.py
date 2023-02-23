from typing import Optional, Tuple
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    InjectFlightRequest,
    InjectFlightResult,
    InjectFlightResponse,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlanner,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    submit_flight_intent,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


def plan_priority_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Attempt to plan a flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in plan_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0015.

    Returns: The injection response.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Incorrectly planned",
        {InjectFlightResult.ConflictWithFlight},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
    )[0]


def modify_planned_priority_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_id: str,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Attempt to modify a planned flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in modify_planned_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0020.

    Returns: The injection response.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Incorrectly modified",
        {InjectFlightResult.ConflictWithFlight},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )[0]


def activate_priority_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_id: str,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Attempt to activate a flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in activate_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0025.

    Returns: The injection response.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Incorrectly activated",
        {InjectFlightResult.ConflictWithFlight},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )[0]


def modify_activated_priority_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_id: str,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Attempt to modify an activated flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in modify_activated_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0030.

    Returns: The injection response.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Incorrectly modified",
        {InjectFlightResult.ConflictWithFlight},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )[0]


def plan_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Attempt to plan a flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in plan_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0035.

    Returns: The injection response.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Incorrectly planned",
        {InjectFlightResult.ConflictWithFlight},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
    )[0]


def modify_planned_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_id: str,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Attempt to modify a planned flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in modify_planned_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0040.

    Returns: The injection response.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Incorrectly modified",
        {InjectFlightResult.ConflictWithFlight},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )[0]


def activate_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_id: str,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Attempt to activate a flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in activate_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0045.

    Returns: The injection response.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Incorrectly activated",
        {InjectFlightResult.ConflictWithFlight},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )[0]


def modify_activated_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_id: str,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Attempt to modify an activated flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in modify_activated_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0050.

    Returns: The injection response.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Incorrectly modified",
        {InjectFlightResult.ConflictWithFlight},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )[0]


def plan_permitted_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
) -> Tuple[InjectFlightResponse, Optional[str]]:
    """Plan a flight intent that has a permitted equal priority conflict with another flight intent, that should result in success.

    This function implements the test step described in plan_permitted_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0055.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Successful planning",
        {InjectFlightResult.Planned},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
    )


def modify_planned_permitted_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_id: str,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Modify a planned flight intent that has a permitted equal priority conflict with another flight intent, that should result in success.

    This function implements the test step described in modify_planned_permitted_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0060.

    Returns: The injection response.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Successful modification",
        {InjectFlightResult.Planned},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )[0]


def activate_permitted_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_id: str,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Activate a flight intent that has a permitted equal priority conflict with another flight intent, that should result in success.

    This function implements the test step described in activate_permitted_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0065.

    Returns: The injection response.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Successful activation",
        {InjectFlightResult.ReadyToFly},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )[0]


def modify_activated_permitted_conflict_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_id: str,
    flight_intent: InjectFlightRequest,
) -> InjectFlightResponse:
    """Modify an activated flight intent that has a permitted equal priority conflict with another flight intent, that should result in success.

    This function implements the test step described in modify_activated_permitted_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0070.

    Returns: The injection response.
    """
    return submit_flight_intent(
        scenario,
        test_step,
        "Successful modification",
        {InjectFlightResult.ReadyToFly},
        {InjectFlightResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )[0]
