import inspect
from collections.abc import Iterable

import arrow
from uas_standards.interuss.automated_testing.flight_planning.v1.api import (
    BasicFlightPlanInformationUasState,
    BasicFlightPlanInformationUsageState,
)

from monitoring.monitorlib.clients.flight_planning.client import PlanningActivityError
from monitoring.monitorlib.clients.flight_planning.client_v1 import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    ExecutionStyle,
    FlightID,
    FlightInfo,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    FlightPlanStatus,
    PlanningActivityResponse,
    PlanningActivityResult,
)
from monitoring.monitorlib.fetch import Query, QueryError
from monitoring.monitorlib.geotemporal import end_time_of
from monitoring.uss_qualifier.scenarios.scenario import (
    ScenarioDidNotStopError,
    TestScenario,
)


def expect_flight_intent_state(
    flight_intent: FlightInfo,
    expected_usage_state: BasicFlightPlanInformationUsageState,
    expected_uas_state: BasicFlightPlanInformationUasState,
    scenario: TestScenario,
) -> None:
    """Confirm that provided flight intent test data has the expected state or raise a ValueError."""
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


def plan_flight(
    scenario: TestScenario,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    additional_fields: dict | None = None,
    nearby_potential_conflict: bool = False,
) -> tuple[PlanningActivityResponse, str | None]:
    """Plan a flight intent that should result in success.

    This function implements the test step fragment described in
    plan_flight_intent.md.

    Parameters:
      nearby_potential_conflict: set to True when there is a nearby flight that may be detected as conflicting by the USS if it does not compute intersection correctly, this will trigger a validation of GEN0500.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """

    resp, flight_id = submit_flight(
        scenario=scenario,
        success_check="Successful planning",
        expected_results={(PlanningActivityResult.Completed, FlightPlanStatus.Planned)},
        failed_checks={PlanningActivityResult.Failed: "Failure"},
        flight_planner=flight_planner,
        flight_info=flight_info,
        additional_fields=additional_fields,
    )

    if (
        nearby_potential_conflict
        and resp.flight_plan_status == FlightPlanStatus.Planned
    ):
        scenario.check(
            "Validate tested USS intersection algorithm", flight_planner.participant_id
        ).record_passed()

    return resp, flight_id


def modify_planned_flight(
    scenario: TestScenario,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: str,
    additional_fields: dict | None = None,
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
        expected_results={
            (PlanningActivityResult.Completed, FlightPlanStatus.Planned),
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


def modify_activated_flight(
    scenario: TestScenario,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: str,
    preexisting_conflict: bool = False,
    additional_fields: dict | None = None,
) -> PlanningActivityResponse:
    """Modify an activated flight intent that should result in success.

    This function implements the test step described in
    modify_activated_flight_intent.md.

    Returns: The injection response.
    """
    expect_flight_intent_state(
        flight_info,
        BasicFlightPlanInformationUsageState.InUse,
        BasicFlightPlanInformationUasState.Nominal,
        scenario,
    )

    if preexisting_conflict:
        resp, _ = submit_flight(
            scenario=scenario,
            success_check="Successful modification",
            expected_results={
                (PlanningActivityResult.Completed, FlightPlanStatus.OkToFly),
                (PlanningActivityResult.NotSupported, FlightPlanStatus.OkToFly),
                # the following results is considered expected in order to fail another check as low severity
                (PlanningActivityResult.Rejected, FlightPlanStatus.OkToFly),
            },
            failed_checks={PlanningActivityResult.Failed: "Failure"},
            flight_planner=flight_planner,
            flight_info=flight_info,
            flight_id=flight_id,
            additional_fields=additional_fields,
        )

        with scenario.check(
            "Rejected modification", [flight_planner.participant_id]
        ) as check:
            if resp.activity_result == PlanningActivityResult.Rejected:
                msg = f"{flight_planner.participant_id} indicated ({resp.activity_result}, {resp.flight_plan_status})"
                if "notes" in resp and resp.notes:
                    msg += f' with notes "{resp.notes}"'
                else:
                    msg += " with no notes"
                check.record_failed(
                    summary="Warning (not a failure): modification got rejected but a pre-existing conflict was present",
                    details=msg,
                )

    else:
        resp, _ = submit_flight(
            scenario=scenario,
            success_check="Successful modification",
            expected_results={
                (PlanningActivityResult.Completed, FlightPlanStatus.OkToFly),
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
        )

    return resp


def activate_flight(
    scenario: TestScenario,
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: str | None = None,
    additional_fields: dict | None = None,
) -> tuple[PlanningActivityResponse, str | None]:
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
    scenario: TestScenario,
    success_check: str,
    expected_results: set[tuple[PlanningActivityResult, FlightPlanStatus]],
    failed_checks: dict[PlanningActivityResult, str],
    flight_planner: FlightPlannerClient,
    flight_info: FlightInfo,
    flight_id: str | None = None,
    additional_fields: dict | None = None,
    skip_if_not_supported: bool = False,
    may_end_in_past: bool = False,
) -> tuple[PlanningActivityResponse, str | None]:
    """Submit a flight intent with an expected result.
    A check fail is considered by default of high severity and as such will raise an ScenarioCannotContinueError.
    The severity of each failed check may be overridden if needed.
    If skip_if_not_supported=True and the USS responds that the operation is not supported, the check is skipped without failing.

    If may_end_in_past=True, this function won't raise an error if the flight intent's end time is in the past.

    This function does not directly implement a test step.

    Returns:
      * The injection response.
      * The ID of the injected flight if it is returned, None otherwise.
    """
    if expected_results.intersection(failed_checks.keys()):
        raise ValueError(
            f"expected and unexpected results overlap: {expected_results.intersection(failed_checks.keys())}"
        )

    if not may_end_in_past:
        intent_end_time = end_time_of(flight_info.basic_information.area)
        if intent_end_time and intent_end_time.datetime < arrow.utcnow():
            raise ValueError(
                f"attempt to submit invalid flight intent: end time is in the past: {intent_end_time}"
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

        msg = f"{flight_planner.participant_id} indicated flight planning activity {resp.activity_result} leaving flight plan {resp.flight_plan_status} rather than the expected {' or '.join([f'(Activity {expected_result[0]}, flight plan {expected_result[1]})' for expected_result in expected_results])}"
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
    flight_id: str | None,
    additional_fields: dict | None = None,
) -> tuple[PlanningActivityResponse, Query, str]:
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


def delete_flight(
    scenario: TestScenario,
    flight_planner: FlightPlannerClient,
    flight_id: FlightID,
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
            resp = flight_planner.try_end_flight(flight_id, ExecutionStyle.IfAllowed)

        except QueryError as e:
            scenario.record_queries(e.queries)
            check.record_failed(
                summary=f"Error from {flight_planner.participant_id} when attempting to delete a flight intent (flight ID: {flight_id})",
                details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                query_timestamps=[q.request.timestamp for q in e.queries],
            )
            raise ScenarioDidNotStopError(check)
        scenario.record_queries(resp.queries)

        notes_suffix = f': "{resp.notes}"' if "notes" in resp and resp.notes else ""

        if (
            resp.activity_result == PlanningActivityResult.Completed
            and resp.flight_plan_status == FlightPlanStatus.Closed
        ):
            flight_planner.created_flight_ids.discard(flight_id)
            return resp
        else:
            check.record_failed(
                summary=f"Flight deletion attempt unexpectedly {resp.activity_result} with flight plan status {resp.flight_plan_status}",
                details=f"{flight_planner.participant_id} indicated {resp.activity_result} with flight plan status {resp.flight_plan_status} rather than the expected Completed with flight plan status Closed{notes_suffix}",
                query_timestamps=[resp.queries[0].request.timestamp]
                if resp.queries
                else [],
            )
            raise ScenarioDidNotStopError(check)


def cleanup_flights(
    scenario: TestScenario, flight_planners: Iterable[FlightPlannerClient]
) -> None:
    """Remove flights during a cleanup test step.

    This function assumes:
    * `scenario` is currently cleaning up (cleanup has started)
    * "Successful flight deletion" check declared for cleanup phase in `scenario`'s documentation
    * IDs of flights created have been added to each flight_planner.created_flight_ids
    """
    for flight_planner in flight_planners:
        to_remove = flight_planner.created_flight_ids.copy()
        for flight_id in to_remove:
            with scenario.check(
                "Successful flight deletion", [flight_planner.participant_id]
            ) as check:
                try:
                    resp = flight_planner.try_end_flight(
                        flight_id, ExecutionStyle.IfAllowed
                    )

                except QueryError as e:
                    scenario.record_queries(e.queries)

                    if (
                        e.queries and e.queries[0].status_code == 404
                    ):  # We allow 404 during cleanup
                        scenario.record_note(
                            f"Deletion of {flight_id}",
                            f"Deletion of flight {flight_id} returned a status code of 404 (instead of a 200)",
                        )

                    else:
                        check.record_failed(
                            summary=f"Failed to clean up flight {flight_id} from {flight_planner.participant_id}",
                            details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                            query_timestamps=[q.request.timestamp for q in e.queries],
                        )

                    # Do not attempt to clean up again as we would expect the same error
                    flight_planner.created_flight_ids.discard(flight_id)

                    continue
                scenario.record_queries(resp.queries)

                if resp.flight_plan_status != FlightPlanStatus.Closed:
                    check.record_failed(
                        summary=f"Failed to clean up flight {flight_id} from {flight_planner.participant_id}",
                        details=f"Deletion of flight {flight_id} returned a status of '{resp.flight_plan_status}' ({FlightPlanStatus.Closed} wanted)",
                        query_timestamps=[q.request.timestamp for q in resp.queries],
                    )

                # Remove flight_id from created flights regardless of status.
                # If status was successful, the flight has been removed.  If the status was unsuccessful, we would
                # expect the same error status if we were to try again.
                flight_planner.created_flight_ids.discard(flight_id)
