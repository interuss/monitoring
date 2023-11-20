import inspect
from typing import Optional, Tuple, Iterable, Set, Dict, Union
from monitoring.monitorlib.clients.flight_planning.client import PlanningActivityError
from monitoring.monitorlib.clients.flight_planning.planning import (
    PlanningActivityResponse,
    PlanningActivityResult,
    FlightPlanStatus,
)

from monitoring.monitorlib.clients.flight_planning.client_v1 import (
    FlightPlannerClient,
)
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    FlightInfo,
    ExecutionStyle,
)
from monitoring.monitorlib.fetch import QueryError, Query

from uas_standards.astm.f3548.v21.api import OperationalIntentState

from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightRequest,
    InjectFlightResponseResult,
    InjectFlightResponse,
    DeleteFlightResponseResult,
    DeleteFlightResponse,
)
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlanner,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


def expect_flight_intent_state(
    flight_intent: InjectFlightRequest,
    expected_state: OperationalIntentState,
    scenario: TestScenarioType,
    test_step: str,
) -> None:
    """Confirm that provided flight intent test data has the expected state or raise a ValueError."""
    if flight_intent.operational_intent.state != expected_state:
        function_name = str(inspect.stack()[1][3])
        raise ValueError(
            f"Error in test data: operational intent state for {function_name} during test step '{test_step}' in scenario '{scenario.documentation.name}' is expected to be `Accepted`, but got `{flight_intent.operational_intent.state}` instead"
        )


def plan_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
) -> Tuple[InjectFlightResponse, Optional[str]]:
    """Plan a flight intent that should result in success.
    Note: This method is deprecated in favor of plan_flight

    This function implements the test step described in
    plan_flight_intent.md.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """
    expect_flight_intent_state(
        flight_intent, OperationalIntentState.Accepted, scenario, test_step
    )

    return submit_flight_intent(
        scenario,
        test_step,
        "Successful planning",
        {InjectFlightResponseResult.Planned},
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
    )


def activate_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
    flight_id: Optional[str] = None,
) -> InjectFlightResponse:
    """Activate a flight intent that should result in success.

    This function implements the test step described in
    activate_flight_intent.md.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_intent, OperationalIntentState.Activated, scenario, test_step
    )

    return submit_flight_intent(
        scenario,
        test_step,
        "Successful activation",
        {InjectFlightResponseResult.ReadyToFly},
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )[0]


def modify_planned_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
    flight_id: str,
) -> InjectFlightResponse:
    """Modify a planned flight intent that should result in success.

    This function implements the test step described in
    modify_planned_flight_intent.md.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_intent, OperationalIntentState.Accepted, scenario, test_step
    )

    return submit_flight_intent(
        scenario,
        test_step,
        "Successful modification",
        {InjectFlightResponseResult.Planned},
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )[0]


def modify_activated_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
    flight_id: str,
    preexisting_conflict: bool = False,
) -> InjectFlightResponse:
    """Attempt to modify an activated flight intent.
    If present, a pre-existing conflict must be indicated with `preexisting_conflict=True`.

    This function implements the test step described in
    modify_activated_flight_intent.md.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_intent, OperationalIntentState.Activated, scenario, test_step
    )

    if preexisting_conflict:
        expected_results = {
            InjectFlightResponseResult.ReadyToFly,
            InjectFlightResponseResult.NotSupported,
            # the following two results are considered expected in order to fail another check as low severity
            InjectFlightResponseResult.Rejected,
            InjectFlightResponseResult.ConflictWithFlight,
        }
        failed_checks = {
            InjectFlightResponseResult.Failed: "Failure",
            InjectFlightResponseResult.Rejected: (
                "Rejected modification",
                Severity.Low,
            ),
            InjectFlightResponseResult.ConflictWithFlight: (
                "Rejected modification",
                Severity.Low,
            ),
        }
    else:
        expected_results = {InjectFlightResponseResult.ReadyToFly}
        failed_checks = {InjectFlightResponseResult.Failed: "Failure"}

    return submit_flight_intent(
        scenario,
        test_step,
        "Successful modification",
        expected_results,
        failed_checks,
        flight_planner,
        flight_intent,
        flight_id,
    )[0]


def submit_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    success_check: str,
    expected_results: Set[InjectFlightResponseResult],
    failed_checks: Dict[InjectFlightResponseResult, Union[str, Tuple[str, Severity]]],
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
    flight_id: Optional[str] = None,
) -> Tuple[InjectFlightResponse, Optional[str]]:
    """Submit a flight intent with an expected result.
    Note: This method is deprecated in favor of submit_flight

    A check fail is considered by default of high severity and as such will raise an ScenarioCannotContinueError.
    The severity of each failed check may be overridden if needed.

    This function does not directly implement a test step.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """
    scenario.begin_test_step(test_step)
    with scenario.check(success_check, [flight_planner.participant_id]) as check:
        try:
            resp, query, flight_id = flight_planner.request_flight(
                flight_intent, flight_id
            )
        except QueryError as e:
            for q in e.queries:
                scenario.record_query(q)
            check.record_failed(
                summary=f"Error from {flight_planner.participant_id} when attempting to submit a flight intent (flight ID: {flight_id})",
                severity=Severity.High,
                details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                query_timestamps=[q.request.timestamp for q in e.queries],
            )
        scenario.record_query(query)
        notes_suffix = f': "{resp.notes}"' if "notes" in resp and resp.notes else ""

        for unexpected_result, failed_test_check in failed_checks.items():
            if isinstance(failed_test_check, str):
                check_name = failed_test_check
                check_severity = Severity.High
            else:
                check_name, check_severity = failed_test_check

            with scenario.check(
                check_name, [flight_planner.participant_id]
            ) as specific_failed_check:
                if resp.result == unexpected_result:
                    specific_failed_check.record_failed(
                        summary=f"Flight unexpectedly {resp.result}",
                        severity=check_severity,
                        details=f'{flight_planner.participant_id} indicated {resp.result} rather than the expected {" or ".join(expected_results)}{notes_suffix}',
                        query_timestamps=[query.request.timestamp],
                    )

        if resp.result in expected_results:
            scenario.end_test_step()
            return resp, flight_id
        else:
            check.record_failed(
                summary=f"Flight unexpectedly {resp.result}",
                severity=Severity.High,
                details=f'{flight_planner.participant_id} indicated {resp.result} rather than the expected {" or ".join(expected_results)}{notes_suffix}',
                query_timestamps=[query.request.timestamp],
            )

    raise RuntimeError(
        "Error with submission of flight intent, but a High Severity issue didn't interrupt execution"
    )


def delete_flight_intent(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlanner,
    flight_id: str,
) -> DeleteFlightResponse:
    """Delete an existing flight intent that should result in success.
    Note: This method is deprecated in favor of delete_flight

    A check fail is considered of high severity and as such will raise an ScenarioCannotContinueError.

    This function implements the test step described in `delete_flight_intent.md`.

    Returns: The deletion response.
    """
    scenario.begin_test_step(test_step)
    with scenario.check(
        "Successful deletion", [flight_planner.participant_id]
    ) as check:
        try:
            resp, query = flight_planner.cleanup_flight(flight_id)
        except QueryError as e:
            for q in e.queries:
                scenario.record_query(q)
            check.record_failed(
                summary=f"Error from {flight_planner.participant_id} when attempting to delete a flight intent (flight ID: {flight_id})",
                severity=Severity.High,
                details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                query_timestamps=[q.request.timestamp for q in e.queries],
            )
        scenario.record_query(query)
        notes_suffix = f': "{resp.notes}"' if "notes" in resp and resp.notes else ""

        if resp.result == DeleteFlightResponseResult.Closed:
            scenario.end_test_step()
            return resp
        else:
            check.record_failed(
                summary=f"Flight deletion attempt unexpectedly {resp.result}",
                severity=Severity.High,
                details=f"{flight_planner.participant_id} indicated {resp.result} rather than the expected {DeleteFlightResponseResult.Closed}{notes_suffix}",
                query_timestamps=[query.request.timestamp],
            )

    raise RuntimeError(
        "Error with deletion of flight intent, but a High Severity issue didn't interrupt execution"
    )


def cleanup_flights(
    scenario: TestScenarioType, flight_planners: Iterable[FlightPlanner]
) -> None:
    """Remove flights during a cleanup test step.
    Note: This method is deprecated in favor of cleanup_flights_fp_client

    This function assumes:
    * `scenario` is currently cleaning up (cleanup has started)
    * "Successful flight deletion" check declared for cleanup phase in `scenario`'s documentation
    """
    for flight_planner in flight_planners:
        removed = []
        to_remove = flight_planner.created_flight_ids.copy()
        for flight_id in to_remove:
            with scenario.check(
                "Successful flight deletion", [flight_planner.participant_id]
            ) as check:
                try:
                    resp, query = flight_planner.cleanup_flight(flight_id)
                    scenario.record_query(query)
                except QueryError as e:
                    for q in e.queries:
                        scenario.record_query(q)
                    check.record_failed(
                        summary=f"Failed to clean up flight {flight_id} from {flight_planner.participant_id}",
                        severity=Severity.Medium,
                        details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                        query_timestamps=[q.request.timestamp for q in e.queries],
                    )
                    continue

                if resp.result == DeleteFlightResponseResult.Closed:
                    removed.append(flight_id)
                else:
                    check.record_failed(
                        summary="Failed to delete flight",
                        details=f"USS indicated: {resp.notes}"
                        if "notes" in resp
                        else "See query",
                        severity=Severity.Medium,
                        query_timestamps=[query.request.timestamp],
                    )


def plan_flight(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    additional_fields: Optional[dict] = None,
) -> Tuple[PlanningActivityResponse, Optional[str]]:
    """Plan a flight intent that should result in success.

    This function implements the test step described in
    plan_flight_intent.md.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """
    return submit_flight(
        scenario=scenario,
        test_step=test_step,
        success_check="Successful planning",
        expected_results={(PlanningActivityResult.Completed, FlightPlanStatus.Planned)},
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        additional_fields=additional_fields,
    )


def submit_flight(
    scenario: TestScenarioType,
    test_step: str,
    success_check: str,
    expected_results: Set[Tuple[PlanningActivityResult, FlightPlanStatus]],
    failed_checks: Dict[PlanningActivityResult, Union[str, Tuple[str, Severity]]],
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: Optional[str] = None,
    additional_fields: Optional[dict] = None,
) -> Tuple[PlanningActivityResponse, Optional[str]]:
    """Submit a flight intent with an expected result.
    A check fail is considered by default of high severity and as such will raise an ScenarioCannotContinueError.
    The severity of each failed check may be overridden if needed.

    This function does not directly implement a test step.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """

    scenario.begin_test_step(test_step)
    with scenario.check(success_check, [flight_planner.participant_id]) as check:
        try:
            resp, query, flight_id = request_flight(
                flight_planner, flight_info, flight_id, additional_fields
            )
        except QueryError as e:
            for q in e.queries:
                scenario.record_query(q)
            check.record_failed(
                summary=f"Error from {flight_planner.participant_id} when attempting to submit a flight intent (flight ID: {flight_id})",
                severity=Severity.High,
                details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                query_timestamps=[q.request.timestamp for q in e.queries],
            )
        scenario.record_query(query)
        notes_suffix = f': "{resp.notes}"' if "notes" in resp and resp.notes else ""

        for unexpected_result, failed_test_check in failed_checks.items():
            if isinstance(failed_test_check, str):
                check_name = failed_test_check
                check_severity = Severity.High
            else:
                check_name, check_severity = failed_test_check

            with scenario.check(
                check_name, [flight_planner.participant_id]
            ) as specific_failed_check:
                if resp.activity_result == unexpected_result:
                    specific_failed_check.record_failed(
                        summary=f"Flight unexpectedly {resp.result}",
                        severity=check_severity,
                        details=f'{flight_planner.participant_id} indicated {resp.result} rather than the expected {" or ".join(expected_results)}{notes_suffix}',
                        query_timestamps=[query.request.timestamp],
                    )

        if (resp.activity_result, resp.flight_plan_status) in expected_results:
            scenario.end_test_step()
            return resp, flight_id
        else:
            check.record_failed(
                summary=f"Flight unexpectedly {resp.result}",
                severity=Severity.High,
                details=f'{flight_planner.participant_id} indicated {resp.result} rather than the expected {" or ".join(expected_results)}{notes_suffix}',
                query_timestamps=[query.request.timestamp],
            )

    raise RuntimeError(
        "Error with submission of flight intent, but a High Severity issue didn't interrupt execution"
    )


def request_flight(
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: Optional[str],
    additional_fields: Optional[dict] = None,
) -> Tuple[PlanningActivityResponse, Query, str]:
    """
    Uses FlightPlannerClient to plan the flight

    Returns:
        * Response from planning activity to request new flight or update existing flight
        * Query used to request planning activity
        * ID of flight
    """
    if not flight_id:
        try:
            resp = flight_planner.try_plan_flight(
                flight_info, ExecutionStyle.IfAllowed, additional_fields
            )
        except PlanningActivityError as e:
            raise QueryError(str(e), e.queries)
        flight_id = resp.flight_id
    else:
        try:
            resp = flight_planner.try_update_flight(
                flight_id, flight_info, ExecutionStyle.IfAllowed
            )
        except PlanningActivityError as e:
            raise QueryError(str(e), e.queries)

    return resp, resp.queries[0], flight_id


def cleanup_flight(
    flight_planner: FlightPlannerClient, flight_id: str
) -> Tuple[PlanningActivityResponse, Query]:

    try:
        resp = flight_planner.try_end_flight(flight_id, ExecutionStyle.IfAllowed)
    except PlanningActivityError as e:
        raise QueryError(str(e), e.queries)

    flight_planner.created_flight_ids.discard(str(flight_id))
    return (
        resp,
        resp.queries[0],
    )


def delete_flight(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlannerClient,
    flight_id: str,
) -> PlanningActivityResponse:
    """Delete an existing flight intent that should result in success.
    A check fail is considered of high severity and as such will raise an ScenarioCannotContinueError.

    This function implements the test step described in `delete_flight_intent.md`.

    Returns: The deletion response.
    """
    scenario.begin_test_step(test_step)
    with scenario.check(
        "Successful deletion", [flight_planner.participant_id]
    ) as check:
        try:
            resp, query = cleanup_flight(flight_planner, flight_id)
        except QueryError as e:
            for q in e.queries:
                scenario.record_query(q)
            check.record_failed(
                summary=f"Error from {flight_planner.participant_id} when attempting to delete a flight intent (flight ID: {flight_id})",
                severity=Severity.High,
                details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                query_timestamps=[q.request.timestamp for q in e.queries],
            )
        scenario.record_query(query)
        notes_suffix = f': "{resp.notes}"' if "notes" in resp and resp.notes else ""

        if (
            resp.activity_result == PlanningActivityResult.Completed
            and resp.flight_plan_status == FlightPlanStatus.Closed
        ):
            scenario.end_test_step()
            return resp
        else:
            check.record_failed(
                summary=f"Flight deletion attempt unexpectedly {(resp.activity_result,resp.flight_plan_status)}",
                severity=Severity.High,
                details=f"{flight_planner.participant_id} indicated {(resp.activity_result,resp.flight_plan_status)} rather than the expected {PlanningActivityResult.Completed,FlightPlanStatus.Closed}{notes_suffix}",
                query_timestamps=[query.request.timestamp],
            )

    raise RuntimeError(
        "Error with deletion of flight intent, but a High Severity issue didn't interrupt execution"
    )


def cleanup_flights_fp_client(
    scenario: TestScenarioType, flight_planners: Iterable[FlightPlannerClient]
) -> None:
    """Remove flights during a cleanup test step.
    Note: This method should be renamed to cleanup_flights once deprecated cleanup_flights method is removed

    This function assumes:
    * `scenario` is currently cleaning up (cleanup has started)
    * "Successful flight deletion" check declared for cleanup phase in `scenario`'s documentation
    """
    for flight_planner in flight_planners:
        removed = []
        to_remove = flight_planner.created_flight_ids.copy()
        for flight_id in to_remove:
            with scenario.check(
                "Successful flight deletion", [flight_planner.participant_id]
            ) as check:
                try:
                    resp, query = cleanup_flight(flight_planner, flight_id)
                    scenario.record_query(query)
                except QueryError as e:
                    for q in e.queries:
                        scenario.record_query(q)
                    check.record_failed(
                        summary=f"Failed to clean up flight {flight_id} from {flight_planner.participant_id}",
                        severity=Severity.Medium,
                        details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                        query_timestamps=[q.request.timestamp for q in e.queries],
                    )
                    continue

                if (
                    resp.activity_result == PlanningActivityResult.Completed
                    and resp.flight_plan_status == FlightPlanStatus.Closed
                ):
                    removed.append(flight_id)
                else:
                    check.record_failed(
                        summary="Failed to delete flight",
                        details=f"USS indicated: {resp.notes}"
                        if "notes" in resp
                        else "See query",
                        severity=Severity.Medium,
                        query_timestamps=[query.request.timestamp],
                    )
