import arrow

from monitoring.monitorlib.geotemporal import resolve_volume4d
from monitoring.uss_qualifier.requirements.definitions import RequirementID
from monitoring.uss_qualifier.resources.interuss.flight_authorization.definitions import (
    FlightCheckTable,
    AcceptanceExpectation,
    ConditionsExpectation,
)
from monitoring.uss_qualifier.resources.interuss.flight_authorization.flight_check_table import (
    FlightCheckTableResource,
)
from monitoring.uss_qualifier.scenarios.documentation.definitions import (
    TestStepDocumentation,
    TestCheckDocumentation,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


_ACCEPT_CHECK_NAME = "Allowed flight"
_REJECT_CHECK_NAME = "Disallowed flight"
_CONDITIONAL_CHECK_NAME = "Required conditions"
_UNCONDITIONAL_CHECK_NAME = "Disallowed conditions"

HARDCODED_PARTICIPANTS_FOR_LAANC = ["USS1"]
"""This constant should not be merged to the main branch -- it is for LAANC notional demonstration only."""


def _get_check_by_name(
    step: TestStepDocumentation, check_name: str
) -> TestCheckDocumentation:
    return [c for c in step.checks if c.name == check_name][0]


class GeneralFlightAuthorization(TestScenario):
    table: FlightCheckTable

    def __init__(
        self,
        table: FlightCheckTableResource,  # TODO: Add new flight planner resource
    ):
        super().__init__()
        self.table = table.table

    def run(self):
        self.begin_test_scenario()

        self.begin_test_case("Flight planning")
        self._plan_flights()
        self.end_test_case()

        self.end_test_scenario()

    def _plan_flights(self):
        start_time = arrow.utcnow().datetime
        for row in self.table.rows:
            checks = []
            if row.acceptance_expectation == AcceptanceExpectation.MustBeAccepted:
                acceptance_check = _get_check_by_name(
                    self._current_case.steps[0], _ACCEPT_CHECK_NAME
                )
                checks.append(acceptance_check)
            elif row.acceptance_expectation == AcceptanceExpectation.MustBeRejected:
                rejection_check = _get_check_by_name(
                    self._current_case.steps[0], _REJECT_CHECK_NAME
                )
                checks.append(rejection_check)
            elif row.acceptance_expectation == AcceptanceExpectation.Irrelevant:
                pass  # No acceptance-related checks to perform in this case
            else:
                raise NotImplementedError(
                    f"expect_to_be_accepted value of {row.expect_to_be_accepted} is not yet supported"
                )

            if row.conditions_expectation == ConditionsExpectation.MustBePresent:
                conditional_check = _get_check_by_name(
                    self._current_case.steps[0], _CONDITIONAL_CHECK_NAME
                )
                checks.append(conditional_check)
            elif row.conditions_expectation == ConditionsExpectation.MustBeAbsent:
                unconditional_check = _get_check_by_name(
                    self._current_case.steps[0], _UNCONDITIONAL_CHECK_NAME
                )
                checks.append(unconditional_check)
            elif row.conditions_expectation == ConditionsExpectation.Irrelevant:
                pass  # No conditions-related checks to perform in this case
            else:
                raise NotImplementedError(
                    f"conditions_expectation value of {row.conditions_expectation} is not yet supported"
                )

            step_checks = [
                TestCheckDocumentation(
                    name=c.name,
                    url=c.url,
                    applicable_requirements=[
                        RequirementID(req) for req in row.requirement_ids
                    ],
                    has_todo=False,
                )
                for c in checks
            ]
            doc = TestStepDocumentation(
                name=row.flight_check_id,
                url=self._current_case.steps[0].url,
                checks=step_checks,
            )
            self.begin_dynamic_test_step(doc)

            concrete_volumes = [resolve_volume4d(v, start_time) for v in row.volumes]

            # TODO: Attempt to plan flight in USSs under test
            self.record_note(
                "flight_planning",
                f"TODO: Attempt to plan flight in USSs where flight plan {row.acceptance_expectation} and conditions {row.conditions_expectation}, from {concrete_volumes[0].time_start} to {concrete_volumes[0].time_end}",
            )

            if row.acceptance_expectation == AcceptanceExpectation.MustBeAccepted:
                with self.check(
                    _ACCEPT_CHECK_NAME, HARDCODED_PARTICIPANTS_FOR_LAANC
                ) as check:  # TODO: Add participant_id
                    pass  # TODO: check USS planning results

            if row.acceptance_expectation == AcceptanceExpectation.MustBeRejected:
                with self.check(
                    _REJECT_CHECK_NAME, HARDCODED_PARTICIPANTS_FOR_LAANC
                ) as check:  # TODO: Add participant_id
                    pass  # TODO: check USS planning results

            # TODO: Only check conditions expectations if flight planning succeeded
            if row.conditions_expectation == ConditionsExpectation.MustBePresent:
                with self.check(
                    _CONDITIONAL_CHECK_NAME, HARDCODED_PARTICIPANTS_FOR_LAANC
                ) as check:  # TODO: Add participant_id
                    pass  # TODO: check USS planning results

            if row.conditions_expectation == ConditionsExpectation.MustBeAbsent:
                with self.check(
                    _UNCONDITIONAL_CHECK_NAME, HARDCODED_PARTICIPANTS_FOR_LAANC
                ) as check:  # TODO: Add participant_id
                    pass  # TODO: check USS planning results

            self.end_test_step()
