from uas_standards.interuss.automated_testing.flight_planning.v1.api import (
    BasicFlightPlanInformationUasState,
    BasicFlightPlanInformationUsageState,
)

from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.clients.flight_planning.planning import (
    FlightPlanStatus,
    PlanningActivityResponse,
    PlanningActivityResult,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    expect_flight_intent_state,
    submit_flight,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


def plan_priority_conflict_flight(
    scenario: TestScenarioType,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    additional_fields: dict | None = None,
) -> PlanningActivityResponse:
    """Attempt to plan a flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in plan_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0015.

    Returns:
      * The injection response.
    """
    expect_flight_intent_state(
        flight_info,
        BasicFlightPlanInformationUsageState.Planned,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    return submit_flight(
        scenario=scenario,
        success_check="Incorrectly planned",
        expected_results={
            (PlanningActivityResult.Rejected, FlightPlanStatus.NotPlanned)
        },
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        additional_fields=additional_fields,
    )[0]


def modify_planned_priority_conflict_flight(
    scenario: TestScenarioType,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: str,
    additional_fields: dict | None = None,
) -> PlanningActivityResponse:
    """Attempt to modify a planned flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in modify_planned_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0020.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_info,
        BasicFlightPlanInformationUsageState.Planned,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    return submit_flight(
        scenario=scenario,
        success_check="Incorrectly modified",
        expected_results={
            (PlanningActivityResult.Rejected, FlightPlanStatus.Planned),
            (
                PlanningActivityResult.Rejected,
                FlightPlanStatus.Closed,
            ),  # case where the USS closes the flight plan as a result of the rejected modification attempt
            (
                PlanningActivityResult.NotSupported,
                FlightPlanStatus.Planned,
            ),  # case where the USS does not support modification of flights
        },
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        flight_id=flight_id,
        additional_fields=additional_fields,
    )[0]


def activate_priority_conflict_flight(
    scenario: TestScenarioType,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: str | None = None,
    additional_fields: dict | None = None,
) -> PlanningActivityResponse:
    """Attempt to activate a flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in activate_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0025.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_info,
        BasicFlightPlanInformationUsageState.InUse,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    return submit_flight(
        scenario=scenario,
        success_check="Incorrectly activated",
        expected_results={
            (
                PlanningActivityResult.Rejected,
                FlightPlanStatus.NotPlanned,
            ),  # case where the activation was about a flight plan not previously planned
            (PlanningActivityResult.Rejected, FlightPlanStatus.Planned),
            (
                PlanningActivityResult.Rejected,
                FlightPlanStatus.Closed,
            ),  # case where the USS closes the flight plan as a result of the rejected activation attempt
        },
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        flight_id=flight_id,
        additional_fields=additional_fields,
    )[0]


def modify_activated_priority_conflict_flight(
    scenario: TestScenarioType,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: str,
    additional_fields: dict | None = None,
) -> PlanningActivityResponse:
    """Attempt to modify an activated flight intent that should result in a conflict with a higher priority flight intent.

    This function implements the test step described in modify_activated_priority_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0030.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_info,
        BasicFlightPlanInformationUsageState.InUse,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    return submit_flight(
        scenario=scenario,
        success_check="Incorrectly modified",
        expected_results={
            (PlanningActivityResult.Rejected, FlightPlanStatus.OkToFly),
            (
                PlanningActivityResult.Rejected,
                FlightPlanStatus.Closed,
            ),  # case where the USS closes the flight plan as a result of the rejected modification attempt; note: is this actually desirable if the flight was activated?
            (
                PlanningActivityResult.NotSupported,
                FlightPlanStatus.OkToFly,
            ),  # case where the USS does not support modification of flights
        },
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        flight_id=flight_id,
        additional_fields=additional_fields,
    )[0]


def plan_conflict_flight(
    scenario: TestScenarioType,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    additional_fields: dict | None = None,
) -> PlanningActivityResponse:
    """Attempt to plan a flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in plan_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0035.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_info,
        BasicFlightPlanInformationUsageState.Planned,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    return submit_flight(
        scenario=scenario,
        success_check="Incorrectly planned",
        expected_results={
            (PlanningActivityResult.Rejected, FlightPlanStatus.NotPlanned)
        },
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        additional_fields=additional_fields,
    )[0]


def modify_planned_conflict_flight(
    scenario: TestScenarioType,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: str,
    additional_fields: dict | None = None,
) -> PlanningActivityResponse:
    """Attempt to modify a planned flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in modify_planned_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0040.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_info,
        BasicFlightPlanInformationUsageState.Planned,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    return submit_flight(
        scenario=scenario,
        success_check="Incorrectly modified",
        expected_results={
            (PlanningActivityResult.Rejected, FlightPlanStatus.Planned),
            (
                PlanningActivityResult.Rejected,
                FlightPlanStatus.Closed,
            ),  # case where the USS closes the flight plan as a result of the rejected modification attempt
            (
                PlanningActivityResult.NotSupported,
                FlightPlanStatus.Planned,
            ),  # case where the USS does not support modification of flights
        },
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        flight_id=flight_id,
        additional_fields=additional_fields,
    )[0]


def activate_conflict_flight(
    scenario: TestScenarioType,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: str | None = None,
    additional_fields: dict | None = None,
) -> PlanningActivityResponse:
    """Attempt to activate a flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in activate_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0045.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_info,
        BasicFlightPlanInformationUsageState.InUse,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    return submit_flight(
        scenario=scenario,
        success_check="Incorrectly activated",
        expected_results={
            (
                PlanningActivityResult.Rejected,
                FlightPlanStatus.NotPlanned,
            ),  # case where the activation was about a flight plan not previously planned
            (PlanningActivityResult.Rejected, FlightPlanStatus.Planned),
            (
                PlanningActivityResult.Rejected,
                FlightPlanStatus.Closed,
            ),  # case where the USS closes the flight plan as a result of the rejected activation attempt
        },
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        flight_id=flight_id,
        additional_fields=additional_fields,
    )[0]


def modify_activated_conflict_flight(
    scenario: TestScenarioType,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: str,
    additional_fields: dict | None = None,
) -> PlanningActivityResponse:
    """Attempt to modify an activated flight intent that should result in a non-permitted conflict with an equal priority flight intent.

    This function implements the test step described in modify_activated_conflict_flight_intent.md.
    It validates requirement astm.f3548.v21.SCD0050.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_info,
        BasicFlightPlanInformationUsageState.InUse,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    return submit_flight(
        scenario=scenario,
        success_check="Incorrectly modified",
        expected_results={
            (PlanningActivityResult.Rejected, FlightPlanStatus.OkToFly),
            (
                PlanningActivityResult.Rejected,
                FlightPlanStatus.Closed,
            ),  # case where the USS closes the flight plan as a result of the rejected modification attempt; note: is this actually desirable if the flight was activated?
            (
                PlanningActivityResult.NotSupported,
                FlightPlanStatus.OkToFly,
            ),  # case where the USS does not support modification of flights
        },
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        flight_id=flight_id,
        additional_fields=additional_fields,
    )[0]
