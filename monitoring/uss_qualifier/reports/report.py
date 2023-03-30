from datetime import datetime
import traceback
from typing import List, Optional, Dict, Tuple, Any, Union, Set, Iterator, Callable

from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.monitorlib import fetch, inspection
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import (
    TestConfiguration,
    ParticipantID,
)
from monitoring.uss_qualifier.fileio import FileReference
from monitoring.uss_qualifier.reports.badge_definitions import BadgeID
from monitoring.uss_qualifier.requirements.definitions import RequirementID


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

    def all_participants(self) -> Set[ParticipantID]:
        participants = set()
        for pc in self.passed_checks:
            for p in pc.participants:
                participants.add(p)
        for fc in self.failed_checks:
            for p in fc.participants:
                participants.add(p)
        return participants

    def query_passed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[PassedCheck]:
        for pc in self.passed_checks:
            if participant_id is None or participant_id in pc.participants:
                yield pc

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[FailedCheck]:
        for fc in self.failed_checks:
            if participant_id is None or participant_id in fc.participants:
                yield fc


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

    def has_critical_problem(self):
        return any(s.has_critical_problem() for s in self.steps)

    def all_participants(self) -> Set[ParticipantID]:
        participants = set()
        for step in self.steps:
            participants = participants.union(step.all_participants())
        return participants

    def query_passed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[PassedCheck]:
        for step in self.steps:
            for pc in step.query_passed_checks(participant_id):
                yield pc

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[FailedCheck]:
        for step in self.steps:
            for fc in step.query_failed_checks(participant_id):
                yield fc


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

    def has_critical_problem(self) -> bool:
        return any(c.has_critical_problem() for c in self.cases) or (
            "cleanup" in self and self.cleanup and self.cleanup.has_critical_problem()
        )

    def all_participants(self) -> Set[ParticipantID]:
        participants = set()
        for case in self.cases:
            participants = participants.union(case.all_participants())
        if "cleanup" in self and self.cleanup:
            participants = participants.union(self.cleanup.all_participants())
        return participants

    def query_passed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[PassedCheck]:
        for case in self.cases:
            for pc in case.query_passed_checks(participant_id):
                yield pc
        if "cleanup" in self and self.cleanup:
            for pc in self.cleanup.query_passed_checks(participant_id):
                yield pc

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[FailedCheck]:
        for case in self.cases:
            for fc in case.query_failed_checks(participant_id):
                yield fc
        if "cleanup" in self and self.cleanup:
            for fc in self.cleanup.query_failed_checks(participant_id):
                yield fc


class ActionGeneratorReport(ImplicitDict):
    generator_type: str
    """Type of action generator"""

    actions: List["TestSuiteActionReport"]
    """Reports from the actions generated by the action generator"""

    @property
    def successful(self) -> bool:
        return all(a.successful() for a in self.actions)

    def has_critical_problem(self) -> bool:
        return any(a.has_critical_problem() for a in self.actions)

    def all_participants(self) -> Set[ParticipantID]:
        participants = set()
        for action in self.actions:
            participants = participants.union(action.all_participants())
        return participants

    def query_passed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[PassedCheck]:
        for action in self.actions:
            for pc in action.query_passed_checks(participant_id):
                yield pc

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[FailedCheck]:
        for action in self.actions:
            for fc in action.query_failed_checks(participant_id):
                yield fc


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

    def _conditional(
        self,
        test_suite_func: Union[
            Callable[["TestSuiteReport"], Any], Callable[[Any], Any]
        ],
        test_scenario_func: Optional[Callable[[TestScenarioReport], Any]] = None,
        action_generator_func: Optional[Callable[[ActionGeneratorReport], Any]] = None,
    ) -> Any:
        test_suite, test_scenario, action_generator = self._get_applicable_report()
        if test_suite:
            return test_suite_func(self.test_suite)
        if test_scenario:
            if test_scenario_func is not None:
                return test_scenario_func(self.test_scenario)
            else:
                return test_suite_func(self.test_scenario)
        if action_generator:
            if action_generator_func is not None:
                return action_generator_func(self.action_generator)
            else:
                return test_suite_func(self.action_generator)

        # This line should not be possible to reach
        raise RuntimeError("Case selection logic failed for TestSuiteActionReport")

    def successful(self) -> bool:
        return self._conditional(lambda report: report.successful)

    def has_critical_problem(self) -> bool:
        return self._conditional(lambda report: report.has_critical_problem())

    def all_participants(self) -> Set[ParticipantID]:
        return self._conditional(lambda report: report.all_participants())

    def query_passed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[PassedCheck]:
        return self._conditional(
            lambda report: report.query_passed_checks(participant_id)
        )

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[FailedCheck]:
        return self._conditional(
            lambda report: report.query_failed_checks(participant_id)
        )


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

    badges_granted: Optional[Dict[ParticipantID, List[BadgeID]]]
    """If badges are defined by this suite, the list of badges earned by each participant."""

    def has_critical_problem(self) -> bool:
        return any(a.has_critical_problem() for a in self.actions)

    def all_participants(self) -> Set[ParticipantID]:
        participants = set()
        for action in self.actions:
            participants = participants.union(action.all_participants())
        return participants

    def query_passed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[PassedCheck]:
        for action in self.actions:
            for pc in action.query_passed_checks(participant_id):
                yield pc

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[FailedCheck]:
        for action in self.actions:
            for fc in action.query_failed_checks(participant_id):
                yield fc


class TestRunReport(ImplicitDict):
    codebase_version: str
    """Version of codebase used to run uss_qualifier"""

    commit_hash: str
    """Full commit hash of codebase used to run uss_qualifier"""

    file_signatures: Dict[str, str]
    """Mapping between the names of files loaded during test run and the SHA-1 hashes of those files' content."""

    baseline_signature: str
    """Signature of the test run including codebase version and all file signatures except excluded environmental files.

    This field can be used to identify that a particular expected test baseline (codebase, all non-environmental inputs)
    was run.  The value of this field is computed from codebase_version and all elements of file_signatures that are not
    explicitly excluded as environmental configuration."""

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
