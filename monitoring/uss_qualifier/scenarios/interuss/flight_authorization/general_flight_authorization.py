import arrow

from monitoring.monitorlib.clients.flight_planning.client import (
    FlightPlannerClient,
    PlanningActivityError,
)
from monitoring.monitorlib.clients.flight_planning.flight_info import ExecutionStyle
from monitoring.monitorlib.clients.flight_planning.planning import (
    AdvisoryInclusion,
    FlightPlanStatus,
    PlanningActivityResult,
)
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.requirements.definitions import RequirementID
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
    FlightPlannerResource,
)
from monitoring.uss_qualifier.resources.interuss.flight_authorization.definitions import (
    AcceptanceExpectation,
    ConditionsExpectation,
    FlightCheckTable,
)
from monitoring.uss_qualifier.resources.interuss.flight_authorization.flight_check_table import (
    FlightCheckTableResource,
)
from monitoring.uss_qualifier.scenarios.documentation.definitions import (
    TestCaseDocumentation,
    TestCheckDocumentation,
    TestScenarioDocumentation,
    TestStepDocumentation,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

# Check names from documentation
_VALID_API_RESPONSE_NAME = "Valid planning response"
_ACCEPT_CHECK_NAME = "Allowed flight"
_REJECT_CHECK_NAME = "Disallowed flight"
_CONDITIONAL_CHECK_NAME = "Required conditions"
_UNCONDITIONAL_CHECK_NAME = "Disallowed conditions"
_SUCCESSFUL_CLOSURE_NAME = "Successful closure"


def _get_check_by_name(
    step: TestStepDocumentation, check_name: str
) -> TestCheckDocumentation:
    return [c for c in step.checks if c.name == check_name][0]


class GeneralFlightAuthorization(TestScenario):
    table: FlightCheckTable
    flight_planner: FlightPlannerClient
    participant_id: ParticipantID

    def __init__(
        self,
        table: FlightCheckTableResource,
        flight_intents: FlightIntentsResource,
        planner: FlightPlannerResource,
    ):
        super().__init__()
        self.table = table.table
        self.flight_planner = planner.client
        self.participant_id = planner.participant_id
        self.flight_intents = flight_intents.get_flight_intents()

    def _rewrite_documentation(self):
        """The documentation in the standard, static accompanying .md file acts as a template, but the test scenario
        dynamically adjusts its test procedure based on the FlightCheckTable provided in configuration."""
        original_case = self.documentation.cases[0]
        original_step = original_case.steps[0]
        steps = []

        for row in self.table.rows:
            # Collect checks applicable to this row/test step
            checks = [
                _get_check_by_name(original_step, name)
                for name in (_VALID_API_RESPONSE_NAME, _SUCCESSFUL_CLOSURE_NAME)
            ]
            if row.acceptance_expectation == AcceptanceExpectation.MustBeAccepted:
                acceptance_check = _get_check_by_name(original_step, _ACCEPT_CHECK_NAME)
                checks.append(acceptance_check)
            elif row.acceptance_expectation == AcceptanceExpectation.MustBeRejected:
                rejection_check = _get_check_by_name(original_step, _REJECT_CHECK_NAME)
                checks.append(rejection_check)
            elif row.acceptance_expectation == AcceptanceExpectation.Irrelevant:
                pass  # No acceptance-related checks to perform in this case
            else:
                raise NotImplementedError(
                    f"expect_to_be_accepted value of {row.expect_to_be_accepted} is not yet supported"
                )

            if row.conditions_expectation == ConditionsExpectation.MustBePresent:
                conditional_check = _get_check_by_name(
                    original_step, _CONDITIONAL_CHECK_NAME
                )
                checks.append(conditional_check)
            elif row.conditions_expectation == ConditionsExpectation.MustBeAbsent:
                unconditional_check = _get_check_by_name(
                    original_step, _UNCONDITIONAL_CHECK_NAME
                )
                checks.append(unconditional_check)
            elif row.conditions_expectation == ConditionsExpectation.Irrelevant:
                pass  # No conditions-related checks to perform in this case
            else:
                raise NotImplementedError(
                    f"conditions_expectation value of {row.conditions_expectation} is not yet supported"
                )

            # Construct documentation for this test step
            step_checks = [
                TestCheckDocumentation(
                    name=c.name,
                    url=c.url,
                    applicable_requirements=[
                        RequirementID(r) for r in row.requirement_ids
                    ],
                    has_todo=c.has_todo,
                    severity=c.severity,
                )
                for c in checks
            ]
            steps.append(
                TestStepDocumentation(
                    name=row.flight_check_id,
                    url=original_step.url,
                    checks=step_checks,
                )
            )

        case = TestCaseDocumentation(
            name=original_case.name,
            url=original_case.url,
            steps=steps,
        )

        new_doc = TestScenarioDocumentation(
            name=self.documentation.name,
            url=self.documentation.url,
            local_path=self.documentation.local_path,
            cases=[case],
        )
        if "resources" in self.documentation:
            new_doc.resources = self.documentation.resources
        if "cleanup" in self.documentation:
            new_doc.cleanup = self.documentation.cleanup
        self.documentation = new_doc

    def run(self, context: ExecutionContext):
        self._rewrite_documentation()
        self.begin_test_scenario(context)
        times = {
            TimeDuringTest.StartOfTestRun: Time(context.start_time),
            TimeDuringTest.StartOfScenario: Time(arrow.utcnow().datetime),
        }

        self.begin_test_case("Flight planning")
        self._plan_flights(times)
        self.end_test_case()

        self.end_test_scenario()

    def _plan_flights(self, times: dict[TimeDuringTest, Time]):
        for row in self.table.rows:
            self.begin_test_step(row.flight_check_id)

            # Attempt planning action
            times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
            info = self.flight_intents[row.flight_intent].resolve(times)
            with self.check(_VALID_API_RESPONSE_NAME, [self.participant_id]) as check:
                try:
                    resp = self.flight_planner.try_plan_flight(
                        info, row.execution_style
                    )
                except PlanningActivityError as e:
                    for q in e.queries:
                        self.record_query(q)
                    check.record_failed(
                        summary="Flight planning API request failed",
                        details=str(e),
                        query_timestamps=[
                            q.request.initiated_at.datetime for q in e.queries
                        ],
                    )
                for q in resp.queries:
                    self.record_query(q)

            # Evaluate acceptance result
            if row.acceptance_expectation == AcceptanceExpectation.MustBeAccepted:
                with self.check(_ACCEPT_CHECK_NAME, [self.participant_id]) as check:
                    if resp.activity_result != PlanningActivityResult.Completed:
                        check.record_failed(
                            summary=f"Expected-accepted flight request was {resp.activity_result}",
                            details=f"The flight was expected to be accepted, but the activity result was indicated as {resp.activity_result}",
                            query_timestamps=[
                                q.request.initiated_at.datetime for q in resp.queries
                            ],
                        )
                    if resp.flight_plan_status not in (
                        FlightPlanStatus.Planned,
                        FlightPlanStatus.OkToFly,
                    ):
                        check.record_failed(
                            summary=f"Expected-accepted flight had {resp.flight_plan_status} flight plan",
                            details=f"The flight was expected to be accepted, but the flight plan status following the planning action was indicated as {resp.flight_plan_status}",
                            query_timestamps=[
                                q.request.initiated_at.datetime for q in resp.queries
                            ],
                        )

            if row.acceptance_expectation == AcceptanceExpectation.MustBeRejected:
                with self.check(_REJECT_CHECK_NAME, [self.participant_id]) as check:
                    if resp.activity_result != PlanningActivityResult.Rejected:
                        check.record_failed(
                            summary=f"Expected-rejected flight request was {resp.activity_result}",
                            details=f"The flight was expected to be rejected, but the activity result was indicated as {resp.activity_result}",
                            query_timestamps=[
                                q.request.initiated_at.datetime for q in resp.queries
                            ],
                        )
                    if resp.flight_plan_status != FlightPlanStatus.NotPlanned:
                        check.record_failed(
                            summary=f"Expected-accepted flight had {resp.flight_plan_status} flight plan",
                            details=f"The flight was expected to be rejected, but the flight plan status following the planning action was indicated as {resp.flight_plan_status}",
                            query_timestamps=[
                                q.request.initiated_at.datetime for q in resp.queries
                            ],
                        )

            # Perform checks only applicable when the planning activity succeeded
            if (
                resp.activity_result == PlanningActivityResult.Completed
                and resp.flight_plan_status
                in (FlightPlanStatus.Planned, FlightPlanStatus.OkToFly)
            ):
                if row.conditions_expectation == ConditionsExpectation.MustBePresent:
                    with self.check(
                        _CONDITIONAL_CHECK_NAME, [self.participant_id]
                    ) as check:
                        if (
                            resp.includes_advisories
                            != AdvisoryInclusion.AtLeastOneAdvisoryOrCondition
                        ):
                            check.record_failed(
                                summary="Missing expected conditions",
                                details=f"The flight planning activity result was expected to be accompanied by conditions/advisories, but advisory inclusion was {resp.includes_advisories}",
                                query_timestamps=[
                                    q.request.initiated_at.datetime
                                    for q in resp.queries
                                ],
                            )

                if row.conditions_expectation == ConditionsExpectation.MustBeAbsent:
                    with self.check(
                        _UNCONDITIONAL_CHECK_NAME, [self.participant_id]
                    ) as check:
                        if (
                            resp.includes_advisories
                            != AdvisoryInclusion.NoAdvisoriesOrConditions
                        ):
                            check.record_failed(
                                summary="Expected-unqualified planning success was qualified by conditions",
                                details=f"The flight planning activity result was expected to be unqualified (accompanied by no conditions/advisories), but advisory inclusion was {resp.includes_advisories}",
                                query_timestamps=[
                                    q.request.initiated_at.datetime
                                    for q in resp.queries
                                ],
                            )

            # Remove flight plan if the activity resulted in a flight plan
            if resp.flight_plan_status in (
                FlightPlanStatus.Planned,
                FlightPlanStatus.OkToFly,
            ):
                with self.check(
                    _VALID_API_RESPONSE_NAME, [self.participant_id]
                ) as check:
                    try:
                        del_resp = self.flight_planner.try_end_flight(
                            resp.flight_id, ExecutionStyle.IfAllowed
                        )
                    except PlanningActivityError as e:
                        for q in e.queries:
                            self.record_query(q)
                        check.record_failed(
                            summary="Flight planning API delete request failed",
                            details=str(e),
                            query_timestamps=[
                                q.request.initiated_at.datetime for q in e.queries
                            ],
                        )
                    for q in del_resp.queries:
                        self.record_query(q)
                with self.check(
                    _SUCCESSFUL_CLOSURE_NAME, [self.participant_id]
                ) as check:
                    if del_resp.flight_plan_status != FlightPlanStatus.Closed:
                        check.record_failed(
                            summary="Could not close flight plan successfully",
                            details=f"Expected flight plan status to be Closed after request to end flight, but status was instead {del_resp.flight_plan_status}",
                            query_timestamps=[
                                q.request.initiated_at.datetime
                                for q in del_resp.queries
                            ],
                        )

            self.end_test_step()
