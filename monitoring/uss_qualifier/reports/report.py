from datetime import datetime
import traceback
from typing import List, Optional, Dict, Tuple, Any, Union, Set

from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.monitorlib import fetch, inspection
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import (
    TestConfiguration,
    ParticipantID,
)
from monitoring.uss_qualifier.fileio import FileReference


RequirementID = str  # TODO: Use uss_qualifier.requirements.documentation.RequirementID


class FailedCheck(ImplicitDict):
    name: str
    """Name of the check that failed"""

    documentation_url: str
    """URL at which the check which failed is described"""

    timestamp: StringBasedDateTime
    """Time the issue was discovered"""

    summary: str
    """Human-readable summary of the issue"""

    details: str
    """Human-readable description of the issue"""

    requirements: List[RequirementID]
    """Requirements that are not met due to this failed check"""

    severity: Severity
    """How severe the issue is"""

    participants: List[ParticipantID]
    """Participants that may not meet the relevant requirements due to this failed check"""

    query_report_timestamps: Optional[List[str]]
    """List of the `report` timestamp field for queries relevant to this failed check"""

    additional_data: Optional[dict]
    """Additional data, structured according to the checks' needs, that may be relevant for understanding this failed check"""


class PassedCheck(ImplicitDict):
    name: str
    """Name of the check that passed"""

    requirements: List[RequirementID]
    """Requirements that would not have been met if this check had failed"""

    participants: List[ParticipantID]
    """Participants that may not have met the relevant requirements if this check had failed"""


class TestStepReport(ImplicitDict):
    name: str
    """Name of this test step"""

    documentation_url: str
    """URL at which this test step is described"""

    start_time: StringBasedDateTime
    """Time at which the test step started"""

    queries: Optional[List[fetch.Query]]
    """Description of HTTP requests relevant to this issue"""

    failed_checks: List[FailedCheck]
    """The checks which failed in this test step"""

    passed_checks: List[PassedCheck]
    """The checks which successfully passed in this test step"""

    end_time: Optional[StringBasedDateTime]
    """Time at which the test step completed or encountered an error"""

    def has_critical_problem(self) -> bool:
        return any(fc.severity == Severity.Critical for fc in self.failed_checks)

    def successful(self) -> bool:
        return False if self.failed_checks else True

    def participants_with_failed_checks(self) -> Set[str]:
        participants = set()
        for fc in self.failed_checks:
            for p in fc.participants:
                participants.add(p)
        return participants


class TestCaseReport(ImplicitDict):
    name: str
    """Name of this test case"""

    documentation_url: str
    """URL at which this test case is described"""

    start_time: StringBasedDateTime
    """Time at which the test case started"""

    end_time: Optional[StringBasedDateTime]
    """Time at which the test case completed or encountered an error"""

    steps: List[TestStepReport]
    """Reports for each of the test steps in this test case"""

    def get_all_failed_checks(self) -> List[FailedCheck]:
        result = []
        for step in self.steps:
            result += step.failed_checks
        return result

    def has_critical_problem(self):
        return any(s.has_critical_problem() for s in self.steps)


class ErrorReport(ImplicitDict):
    type: str
    """Type of error"""

    message: str
    """Error message"""

    timestamp: StringBasedDateTime
    """Time at which the error was logged"""

    stacktrace: str
    """Full stack trace of error"""

    @staticmethod
    def create_from_exception(e: Exception):
        return ErrorReport(
            type=str(inspection.fullname(e.__class__)),
            message=str(e),
            timestamp=StringBasedDateTime(datetime.utcnow()),
            stacktrace="".join(
                traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            ),
        )


class Note(ImplicitDict):
    message: str
    timestamp: StringBasedDateTime


class TestScenarioReport(ImplicitDict):
    name: str
    """Name of this test scenario"""

    scenario_type: str
    """Type of this test scenario"""

    documentation_url: str
    """URL at which this test scenario is described"""

    notes: Optional[Dict[str, Note]]
    """Additional information about this scenario that may be useful"""

    start_time: StringBasedDateTime
    """Time at which the test scenario started"""

    end_time: Optional[StringBasedDateTime]
    """Time at which the test scenario completed or encountered an error"""

    successful: bool = False
    """True iff test scenario completed normally with no failed checks"""

    cases: List[TestCaseReport]
    """Reports for each of the test cases in this test scenario"""

    cleanup: Optional[TestStepReport]
    """If this test scenario performed cleanup, this report captures the relevant information."""

    execution_error: Optional[ErrorReport]
    """If there was an error while executing this test scenario, this field describes the error"""

    def get_all_failed_checks(self) -> List[FailedCheck]:
        result = []
        for case in self.cases:
            result += case.get_all_failed_checks()
        return result

    def has_critical_problem(self) -> bool:
        return any(c.has_critical_problem() for c in self.cases) or (
            "cleanup" in self and self.cleanup and self.cleanup.has_critical_problem()
        )


class ActionGeneratorReport(ImplicitDict):
    generator_type: str
    """Type of action generator"""

    actions: List["TestSuiteActionReport"]
    """Reports from the actions generated by the action generator"""

    def successful(self) -> bool:
        return all(a.successful() for a in self.actions)

    def has_critical_problem(self) -> bool:
        return any(a.has_critical_problem() for a in self.actions)


class TestSuiteActionReport(ImplicitDict):
    test_suite: Optional["TestSuiteReport"]
    """If this action was a test suite, this field will hold its report"""

    test_scenario: Optional[TestScenarioReport]
    """If this action was a test scenario, this field will hold its report"""

    action_generator: Optional[ActionGeneratorReport]
    """If this action was an action generator, this field will hold its report"""

    def _get_applicable_report(self) -> Tuple[bool, bool, bool]:
        test_suite = "test_suite" in self and self.test_suite is not None
        test_scenario = "test_scenario" in self and self.test_scenario is not None
        action_generator = (
            "action_generator" in self and self.action_generator is not None
        )
        if (
            sum(
                1 if case else 0
                for case in [test_suite, test_scenario, action_generator]
            )
            != 1
        ):
            raise ValueError(
                "Exactly one of `test_suite`, `test_scenario`, or `action_generator` must be populated"
            )
        return test_suite, test_scenario, action_generator

    def successful(self) -> bool:
        test_suite, test_scenario, action_generator = self._get_applicable_report()
        if test_suite:
            return self.test_suite.successful
        if test_scenario:
            return self.test_scenario.successful
        if action_generator:
            return self.action_generator.successful()

        # This line should not be possible to reach
        raise RuntimeError("Case selection logic failed for TestSuiteActionReport")

    def has_critical_problem(self) -> bool:
        test_suite, test_scenario, action_generator = self._get_applicable_report()
        if test_scenario:
            return self.test_scenario.has_critical_problem()
        if test_suite:
            return self.test_suite.has_critical_problem()
        if action_generator:
            return self.action_generator.has_critical_problem()

        # This line should not be possible to reach
        raise RuntimeError("Case selection logic failed for TestSuiteActionReport")


class TestSuiteReport(ImplicitDict):
    name: str
    """Name of this test suite"""

    suite_type: FileReference
    """Type/location of this test suite"""

    documentation_url: str
    """URL at which this test suite is described"""

    start_time: StringBasedDateTime
    """Time at which the test suite started"""

    actions: List[TestSuiteActionReport]
    """Reports from test scenarios and test suites comprising the test suite for this report"""

    end_time: Optional[StringBasedDateTime]
    """Time at which the test suite completed"""

    successful: bool = False
    """True iff test suite completed normally with no failed checks"""

    def has_critical_problem(self) -> bool:
        return any(a.has_critical_problem() for a in self.actions)


class TestRunReport(ImplicitDict):
    codebase_version: str
    """Version of codebase used to run uss_qualifier"""

    configuration: TestConfiguration
    """Configuration used to run uss_qualifier"""

    report: TestSuiteActionReport
    """Report produced by configured test action"""


def redact_access_tokens(report: Union[Dict[str, Any], list]) -> None:
    if isinstance(report, dict):
        changes = {}
        for k, v in report.items():
            if (
                k.lower() == "authorization"
                and isinstance(v, str)
                and v.lower().startswith("bearer ")
            ):
                token_parts = v[len("bearer ") :].split(".")
                token_parts[-1] = "REDACTED"
                changes[k] = v[0 : len("bearer ")] + ".".join(token_parts)
            elif isinstance(v, dict) or isinstance(v, list):
                redact_access_tokens(v)
        for k, v in changes.items():
            report[k] = v
    elif isinstance(report, list):
        for item in report:
            if isinstance(item, dict) or isinstance(item, list):
                redact_access_tokens(item)
    else:
        raise ValueError(f"{type(report).__name__} is not a dict or list")
