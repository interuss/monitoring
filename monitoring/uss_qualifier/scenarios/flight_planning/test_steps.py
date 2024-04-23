import inspect
from typing import Optional, Tuple, Iterable, Set, Dict, Union

from monitoring.monitorlib.deprecation import assert_deprecated, CallSite
from uas_standards.interuss.automated_testing.flight_planning.v1.api import (
    BasicFlightPlanInformationUsageState,
    BasicFlightPlanInformationUasState,
)

from monitoring.monitorlib.clients.flight_planning.client import PlanningActivityError
from monitoring.monitorlib.clients.flight_planning.planning import (
    PlanningActivityResponse,
    PlanningActivityResult,
    FlightPlanStatus,
    AdvisoryInclusion,
)

from monitoring.monitorlib.clients.flight_planning.client_v1 import (
    FlightPlannerClient,
)
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    FlightInfo,
    ExecutionStyle,
)
from monitoring.monitorlib.fetch import QueryError, Query

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
    flight_intent: Union[InjectFlightRequest, FlightInfo],
    expected_usage_state: BasicFlightPlanInformationUsageState,
    expected_uas_state: BasicFlightPlanInformationUasState,
    scenario: TestScenarioType,
) -> None:
    """Confirm that provided flight intent test data has the expected state or raise a ValueError."""
    if isinstance(flight_intent, InjectFlightRequest):
        flight_intent = FlightInfo.from_scd_inject_flight_request(flight_intent)

    function_name = str(inspect.stack()[1][3])
    test_step = scenario.current_step_name()
    if flight_intent.basic_information.usage_state != expected_usage_state:
        raise ValueError(
            f"Error in test data: usage state for {function_name} during test step '{test_step}' in scenario '{scenario.documentation.name}' is expected to be `{expected_usage_state}`, but got `{flight_intent.basic_information.usage_state}` instead"
        )
    if flight_intent.basic_information.uas_state != expected_uas_state:
        raise ValueError(
            f"Error in test data: UAS state for {function_name} during test step '{test_step}' in scenario '{scenario.documentation.name}' is expected to be `{expected_uas_state}`, but got `{flight_intent.basic_information.uas_state}` instead"
        )


def plan_flight_intent(
    scenario: TestScenarioType,
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
) -> Tuple[InjectFlightResponse, Optional[str], Optional[AdvisoryInclusion]]:
    """Plan a flight intent that should result in success.
    Note: This method is deprecated in favor of plan_flight

    This function implements the test step described in
    plan_flight_intent.md.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """
    assert_deprecated(
        legacy_callers=[
            CallSite(
                "_validate_ended_cancellation",
                "monitoring/uss_qualifier/scenarios/astm/utm/flight_intent_validation/flight_intent_validation.py",
            ),
            CallSite(
                "_validate_precision_intersection",
                "monitoring/uss_qualifier/scenarios/astm/utm/flight_intent_validation/flight_intent_validation.py",
            ),
            CallSite(
                "_attempt_modify_planned_flight_conflict",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_equal_priority_not_permitted/conflict_equal_priority_not_permitted.py",
            ),
            CallSite(
                "_attempt_plan_flight_conflict",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_equal_priority_not_permitted/conflict_equal_priority_not_permitted.py",
            ),
            CallSite(
                "_modify_activated_flight_preexisting_conflict",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_equal_priority_not_permitted/conflict_equal_priority_not_permitted.py",
            ),
            CallSite(
                "_attempt_modify_planned_flight_conflict",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_higher_priority/conflict_higher_priority.py",
            ),
            CallSite(
                "_attempt_plan_flight_conflict",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_higher_priority/conflict_higher_priority.py",
            ),
            CallSite(
                "_modify_activated_flight_conflict_preexisting",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_higher_priority/conflict_higher_priority.py",
            ),
            CallSite(
                "_plan_valid_flight",
                "monitoring/uss_qualifier/scenarios/uspace/flight_auth/validation.py",
            ),
        ]
    )
    expect_flight_intent_state(
        flight_intent,
        BasicFlightPlanInformationUsageState.Planned,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    resp, flight_id, advisories = submit_flight_intent(
        scenario,
        "Successful planning",
        {InjectFlightResponseResult.Planned},
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
    )

    return resp, flight_id, advisories


def activate_flight_intent(
    scenario: TestScenarioType,
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
        flight_intent,
        BasicFlightPlanInformationUsageState.InUse,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    resp, _, _ = submit_flight_intent(
        scenario,
        "Successful activation",
        {InjectFlightResponseResult.ReadyToFly},
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )

    return resp


def modify_planned_flight_intent(
    scenario: TestScenarioType,
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
        flight_intent,
        BasicFlightPlanInformationUsageState.Planned,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    resp, _, _ = submit_flight_intent(
        scenario,
        "Successful modification",
        {InjectFlightResponseResult.Planned},
        {InjectFlightResponseResult.Failed: "Failure"},
        flight_planner,
        flight_intent,
        flight_id,
    )

    return resp


def modify_activated_flight_intent(
    scenario: TestScenarioType,
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
        flight_intent,
        BasicFlightPlanInformationUsageState.InUse,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    if preexisting_conflict:
        resp, flight_id, _ = submit_flight_intent(
            scenario,
            "Successful modification",
            {
                InjectFlightResponseResult.ReadyToFly,
                InjectFlightResponseResult.NotSupported,
                # the following two results are considered expected in order to fail another check as low severity
                InjectFlightResponseResult.Rejected,
                InjectFlightResponseResult.ConflictWithFlight,
            },
            {
                InjectFlightResponseResult.Failed: "Failure",
            },
            flight_planner,
            flight_intent,
            flight_id,
        )

        with scenario.check(
            "Rejected modification", [flight_planner.participant_id]
        ) as check:
            if (
                resp.result == InjectFlightResponseResult.Rejected
                or resp.result == InjectFlightResponseResult.ConflictWithFlight
            ):
                msg = f"{flight_planner.participant_id} indicated {resp.result}"
                if "notes" in resp and resp.notes:
                    msg += f' with notes "{resp.notes}"'
                else:
                    msg += " with no notes"
                check.record_failed(
                    summary="Warning (not a failure): modification got rejected but a pre-existing conflict was present",
                    severity=Severity.Low,
                    details=msg,
                )

    else:
        resp, flight_id, _ = submit_flight_intent(
            scenario,
            "Successful modification",
            {InjectFlightResponseResult.ReadyToFly},
            {InjectFlightResponseResult.Failed: "Failure"},
            flight_planner,
            flight_intent,
            flight_id,
        )

    return resp


def submit_flight_intent(
    scenario: TestScenarioType,
    success_check: str,
    expected_results: Set[InjectFlightResponseResult],
    failed_checks: Dict[InjectFlightResponseResult, str],
    flight_planner: FlightPlanner,
    flight_intent: InjectFlightRequest,
    flight_id: Optional[str] = None,
) -> Tuple[InjectFlightResponse, Optional[str], Optional[AdvisoryInclusion]]:
    """Submit a flight intent with an expected result.
    Note: This method is deprecated in favor of submit_flight

    A check fail is considered by default of high severity and as such will raise an ScenarioCannotContinueError.
    The severity of each failed check may be overridden if needed.

    This function does not directly implement a test step.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """
    assert_deprecated(
        legacy_callers=[
            CallSite(
                "_attempt_invalid",
                "monitoring/uss_qualifier/scenarios/astm/utm/flight_intent_validation/flight_intent_validation.py",
            ),
            CallSite(
                "_validate_precision_intersection",
                "monitoring/uss_qualifier/scenarios/astm/utm/flight_intent_validation/flight_intent_validation.py",
            ),
            CallSite(
                "_modify_activated_flight_preexisting_conflict",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_equal_priority_not_permitted/conflict_equal_priority_not_permitted.py",
            ),
            CallSite(
                "_plan_flight_conflict_planned",
                "monitoring/uss_qualifier/scenarios/astm/utm/off_nominal_planning/down_uss.py",
            ),
            CallSite(
                "_plan_flight_conflict_activated",
                "monitoring/uss_qualifier/scenarios/astm/utm/off_nominal_planning/down_uss_equal_priority_not_permitted.py",
            ),
            CallSite(
                "_plan_flight_conflict_contingent",
                "monitoring/uss_qualifier/scenarios/astm/utm/off_nominal_planning/down_uss_equal_priority_not_permitted.py",
            ),
            CallSite(
                "_plan_flight_conflict_nonconforming",
                "monitoring/uss_qualifier/scenarios/astm/utm/off_nominal_planning/down_uss_equal_priority_not_permitted.py",
            ),
            CallSite(
                "activate_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "activate_permitted_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "activate_priority_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "modify_activated_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "modify_activated_permitted_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "modify_activated_priority_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "modify_planned_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "modify_planned_permitted_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "modify_planned_priority_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "plan_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "plan_permitted_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "plan_priority_conflict_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/prioritization_test_steps.py",
            ),
            CallSite(
                "activate_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/test_steps.py",
            ),
            CallSite(
                "modify_activated_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/test_steps.py",
            ),
            CallSite(
                "modify_planned_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/test_steps.py",
            ),
            CallSite(
                "plan_flight_intent",
                "monitoring/uss_qualifier/scenarios/flight_planning/test_steps.py",
            ),
        ]
    )
    if expected_results.intersection(failed_checks.keys()):
        raise ValueError(
            f"expected and unexpected results overlap: {expected_results.intersection(failed_checks.keys())}"
        )

    with scenario.check(success_check, [flight_planner.participant_id]) as check:
        try:
            resp, query, flight_id, advisories = flight_planner.request_flight(
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
        msg = f'{flight_planner.participant_id} indicated {resp.result} rather than the expected {" or ".join(expected_results)}'
        if "notes" in resp and resp.notes:
            msg += f' with notes "{resp.notes}"'
        else:
            msg += " with no notes"

        if resp.result not in expected_results:
            check.record_failed(
                summary=f"Flight unexpectedly {resp.result}",
                severity=Severity.High,
                details=msg,
                query_timestamps=[query.request.timestamp],
            )

    for failed_result, failed_check_name in failed_checks.items():
        with scenario.check(
            failed_check_name,
            [flight_planner.participant_id],
        ) as check:
            if resp.result == failed_result:
                check.record_failed(
                    summary=f"Flight unexpectedly {resp.result}",
                    severity=Severity.High,
                    details=msg,
                    query_timestamps=[query.request.timestamp],
                )

    return resp, flight_id, advisories


def delete_flight_intent(
    scenario: TestScenarioType,
    flight_planner: FlightPlanner,
    flight_id: str,
) -> DeleteFlightResponse:
    """Delete an existing flight intent that should result in success.
    Note: This method is deprecated in favor of delete_flight

    A check fail is considered of high severity and as such will raise an ScenarioCannotContinueError.

    This function implements the test step described in `delete_flight_intent.md`.

    Returns: The deletion response.
    """
    assert_deprecated(
        legacy_callers=[
            CallSite(
                "_validate_ended_cancellation",
                "monitoring/uss_qualifier/scenarios/astm/utm/flight_intent_validation/flight_intent_validation.py",
            ),
            CallSite(
                "_attempt_modify_activated_flight_conflict",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_equal_priority_not_permitted/conflict_equal_priority_not_permitted.py",
            ),
            CallSite(
                "_attempt_plan_flight_conflict",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_higher_priority/conflict_higher_priority.py",
            ),
            CallSite(
                "_modify_activated_flight_conflict_preexisting",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_higher_priority/conflict_higher_priority.py",
            ),
        ]
    )
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
    assert_deprecated(
        legacy_callers=[
            CallSite(
                "cleanup",
                "monitoring/uss_qualifier/scenarios/astm/utm/flight_intent_validation/flight_intent_validation.py",
            ),
            CallSite(
                "cleanup",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_equal_priority_not_permitted/conflict_equal_priority_not_permitted.py",
            ),
            CallSite(
                "cleanup",
                "monitoring/uss_qualifier/scenarios/astm/utm/nominal_planning/conflict_higher_priority/conflict_higher_priority.py",
            ),
            CallSite(
                "cleanup",
                "monitoring/uss_qualifier/scenarios/astm/utm/off_nominal_planning/down_uss.py",
            ),
            CallSite(
                "cleanup",
                "monitoring/uss_qualifier/scenarios/uspace/flight_auth/validation.py",
            ),
        ]
    )
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
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    additional_fields: Optional[dict] = None,
) -> Tuple[PlanningActivityResponse, Optional[str]]:
    """Plan a flight intent that should result in success.

    This function implements the test step fragment described in
    plan_flight_intent.md.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """
    return submit_flight(
        scenario=scenario,
        success_check="Successful planning",
        expected_results={(PlanningActivityResult.Completed, FlightPlanStatus.Planned)},
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        additional_fields=additional_fields,
    )


def modify_planned_flight(
    scenario: TestScenarioType,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: str,
    additional_fields: Optional[dict] = None,
) -> PlanningActivityResponse:
    """Modify a planned flight intent that should result in success.

    This function implements the test step described in
    modify_planned_flight_intent.md.

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
        success_check="Successful modification",
        expected_results={(PlanningActivityResult.Completed, FlightPlanStatus.Planned)},
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        flight_id=flight_id,
        additional_fields=additional_fields,
    )[0]


def activate_flight(
    scenario: TestScenarioType,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: Optional[str] = None,
    additional_fields: Optional[dict] = None,
) -> Tuple[PlanningActivityResponse, Optional[str]]:
    """Activate a flight intent that should result in success.

    This function implements the test step fragment described in
    activate_flight_intent.md.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """
    return submit_flight(
        scenario=scenario,
        success_check="Successful activation",
        expected_results={(PlanningActivityResult.Completed, FlightPlanStatus.OkToFly)},
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        flight_id=flight_id,
        additional_fields=additional_fields,
    )


def submit_flight(
    scenario: TestScenarioType,
    success_check: str,
    expected_results: Set[Tuple[PlanningActivityResult, FlightPlanStatus]],
    failed_checks: Dict[PlanningActivityResult, str],
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: Optional[str] = None,
    additional_fields: Optional[dict] = None,
    skip_if_not_supported: bool = False,
) -> Tuple[PlanningActivityResponse, Optional[str]]:
    """Submit a flight intent with an expected result.
    A check fail is considered by default of high severity and as such will raise an ScenarioCannotContinueError.
    The severity of each failed check may be overridden if needed.
    If skip_if_not_supported=True and the USS responds that the operation is not supported, the check is skipped without failing.

    This function does not directly implement a test step.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """
    if expected_results.intersection(failed_checks.keys()):
        raise ValueError(
            f"expected and unexpected results overlap: {expected_results.intersection(failed_checks.keys())}"
        )

    with scenario.check(success_check, [flight_planner.participant_id]) as check:
        try:
            resp, query, flight_id = request_flight(
                flight_planner, flight_info, flight_id, additional_fields
            )
            scenario.record_query(query)
        except QueryError as e:
            scenario.record_queries(e.queries)
            check.record_failed(
                summary=f"Error from {flight_planner.participant_id} when attempting to submit a flight intent (flight ID: {flight_id})",
                details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                query_timestamps=[q.request.timestamp for q in e.queries],
            )

        if (
            skip_if_not_supported
            and resp.activity_result == PlanningActivityResult.NotSupported
        ):
            check.skip()
            return resp, None

        msg = f'{flight_planner.participant_id} indicated flight planning activity {resp.activity_result} leaving flight plan {resp.flight_plan_status} rather than the expected {" or ".join([f"(Activity {expected_result[0]}, flight plan {expected_result[1]})" for expected_result in expected_results])}'
        if "notes" in resp and resp.notes:
            msg += f' with notes "{resp.notes}"'
        else:
            msg += " with no notes"

        for unexpected_result, check_name in failed_checks.items():
            with scenario.check(
                check_name, [flight_planner.participant_id]
            ) as specific_failed_check:
                if resp.activity_result == unexpected_result:
                    specific_failed_check.record_failed(
                        summary=f"Flight planning activity {resp.activity_result} leaving flight plan {resp.flight_plan_status}",
                        details=msg,
                        query_timestamps=[query.request.timestamp],
                    )

        if (resp.activity_result, resp.flight_plan_status) not in expected_results:
            check.record_failed(
                summary=f"Flight planning activity unexpectedly {resp.activity_result} leaving flight plan {resp.flight_plan_status}",
                details=msg,
                query_timestamps=[query.request.timestamp],
            )

    return resp, flight_id


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
    flight_planner: FlightPlannerClient,
    flight_id: str,
) -> PlanningActivityResponse:
    """Delete an existing flight intent that should result in success.
    A check fail is considered of high severity and as such will raise an ScenarioCannotContinueError.

    This function implements the test step described in `delete_flight_intent.md`.

    Returns: The deletion response.
    """
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
            return resp
        else:
            check.record_failed(
                summary=f"Flight deletion attempt unexpectedly {resp.activity_result} with flight plan status {resp.flight_plan_status}",
                severity=Severity.High,
                details=f"{flight_planner.participant_id} indicated {resp.activity_result} with flight plan status {resp.flight_plan_status} rather than the expected Completed with flight plan status Closed{notes_suffix}",
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
                        details=f"USS indicated {resp.activity_result} with flight plan status {resp.flight_plan_status} rather than the expected Completed with flight plan status Closed.  Its notes were: {resp.notes}"
                        if "notes" in resp
                        else "See query",
                        severity=Severity.Medium,
                        query_timestamps=[query.request.timestamp],
                    )
