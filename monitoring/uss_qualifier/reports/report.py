from __future__ import annotations

from datetime import datetime
import traceback
from typing import List, Optional, Dict, Tuple, Any, Union, Set, Iterator, Callable

from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.monitorlib import fetch, inspection
from monitoring.uss_qualifier.action_generators.definitions import GeneratorTypeName
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import (
    TestConfiguration,
    ParticipantID,
)
from monitoring.uss_qualifier.fileio import FileReference
from monitoring.uss_qualifier.reports.capability_definitions import (
    CapabilityID,
    JSONPathExpression,
)
from monitoring.uss_qualifier.requirements.definitions import RequirementID
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioTypeName
from monitoring.uss_qualifier.suites.definitions import TestSuiteActionDeclaration


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

    timestamp: StringBasedDateTime
    """Time the issue was discovered"""

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
    ) -> Iterator[Tuple[JSONPathExpression, PassedCheck]]:
        for i, pc in enumerate(self.passed_checks):
            if participant_id is None or participant_id in pc.participants:
                yield f"passed_checks[{i}]", pc

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[Tuple[JSONPathExpression, PassedCheck]]:
        for i, fc in enumerate(self.failed_checks):
            if participant_id is None or participant_id in fc.participants:
                yield f"failed_checks[{i}]", fc

    def participant_ids(self) -> Set[ParticipantID]:
        ids = set()
        for pc in self.passed_checks:
            ids.update(pc.participants)
        for fc in self.failed_checks:
            ids.update(fc.participants)
        return ids


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
    """Reports for each of the test steps in this test case, in chronological order."""

    def has_critical_problem(self):
        return any(s.has_critical_problem() for s in self.steps)

    def all_participants(self) -> Set[ParticipantID]:
        participants = set()
        for step in self.steps:
            participants = participants.union(step.all_participants())
        return participants

    def query_passed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[Tuple[JSONPathExpression, PassedCheck]]:
        for i, step in enumerate(self.steps):
            for path, pc in step.query_passed_checks(participant_id):
                yield f"steps[{i}].{path}", pc

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[Tuple[JSONPathExpression, PassedCheck]]:
        for i, step in enumerate(self.steps):
            for path, fc in step.query_failed_checks(participant_id):
                yield f"steps[{i}].{path}", fc

    def participant_ids(self) -> Set[ParticipantID]:
        ids = set()
        for step in self.steps:
            ids.update(step.participant_ids())
        return ids


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
            stacktrace="".join(traceback.format_exception(e)),
        )


class Note(ImplicitDict):
    message: str
    timestamp: StringBasedDateTime


class TestScenarioReport(ImplicitDict):
    name: str
    """Name of this test scenario"""

    scenario_type: TestScenarioTypeName
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
    """Reports for each of the test cases in this test scenario, in chronological order."""

    cleanup: Optional[TestStepReport]
    """If this test scenario performed cleanup, this report captures the relevant information."""

    execution_error: Optional[ErrorReport]
    """If there was an error while executing this test scenario, this field describes the error"""

    def has_critical_problem(self) -> bool:
        if any(c.has_critical_problem() for c in self.cases):
            return True
        if "cleanup" in self and self.cleanup and self.cleanup.has_critical_problem():
            return True
        if "execution_error" in self and self.execution_error:
            return True
        return False

    def all_participants(self) -> Set[ParticipantID]:
        participants = set()
        for case in self.cases:
            participants = participants.union(case.all_participants())
        if "cleanup" in self and self.cleanup:
            participants = participants.union(self.cleanup.all_participants())
        return participants

    def query_passed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[Tuple[JSONPathExpression, PassedCheck]]:
        for i, case in enumerate(self.cases):
            for path, pc in case.query_passed_checks(participant_id):
                yield f"cases[{i}].{path}", pc
        if "cleanup" in self and self.cleanup:
            for path, pc in self.cleanup.query_passed_checks(participant_id):
                yield f"cleanup.{path}", pc

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[Tuple[JSONPathExpression, FailedCheck]]:
        for i, case in enumerate(self.cases):
            for path, fc in case.query_failed_checks(participant_id):
                yield f"cases[{i}].{path}", fc
        if "cleanup" in self and self.cleanup:
            for path, fc in self.cleanup.query_failed_checks(participant_id):
                yield f"cleanup.{path}", fc

    def queries(self) -> List[fetch.Query]:
        queries = list()
        for case in self.cases:
            for step in case.steps:
                if step.has_field_with_value("queries"):
                    queries.extend(step.queries)

        if self.has_field_with_value("cleanup") and self.cleanup.has_field_with_value(
            "queries"
        ):
            queries.extend(self.cleanup.queries)

        return queries

    def participant_ids(self) -> Set[ParticipantID]:
        ids = set()
        for case in self.cases:
            ids.update(case.participant_ids())
        if "cleanup" in self and self.cleanup:
            ids.update(self.cleanup.participant_ids())
        return ids


class ActionGeneratorReport(ImplicitDict):
    generator_type: GeneratorTypeName
    """Type of action generator"""

    start_time: StringBasedDateTime
    """Time at which the action generator started"""

    actions: List[TestSuiteActionReport]
    """Reports from the actions generated by the action generator, in order of execution."""

    end_time: Optional[StringBasedDateTime]
    """Time at which the action generator completed or encountered an error"""

    successful: bool = False
    """True iff all actions completed normally with no failed checks"""

    def has_critical_problem(self) -> bool:
        return any(a.has_critical_problem() for a in self.actions)

    def all_participants(self) -> Set[ParticipantID]:
        participants = set()
        for action in self.actions:
            participants = participants.union(action.all_participants())
        return participants

    def query_passed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[Tuple[JSONPathExpression, PassedCheck]]:
        for i, action in enumerate(self.actions):
            for path, pc in action.query_passed_checks(participant_id):
                yield f"actions[{i}].{path}", pc

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[Tuple[JSONPathExpression, PassedCheck]]:
        for i, action in enumerate(self.actions):
            for path, fc in action.query_failed_checks(participant_id):
                yield f"actions[{i}].{path}", fc

    def queries(self) -> List[fetch.Query]:
        queries = list()
        for action in self.actions:
            queries.extend(action.queries())
        return queries

    def participant_ids(self) -> Set[ParticipantID]:
        ids = set()
        for action in self.actions:
            ids.update(action.participant_ids())
        return ids


class TestSuiteActionReport(ImplicitDict):
    test_suite: Optional[TestSuiteReport]
    """If this action was a test suite, this field will hold its report"""

    test_scenario: Optional[TestScenarioReport]
    """If this action was a test scenario, this field will hold its report"""

    action_generator: Optional[ActionGeneratorReport]
    """If this action was an action generator, this field will hold its report"""

    skipped_action: Optional[SkippedActionReport]
    """If this action was skipped, this field will hold its report"""

    def get_applicable_report(self) -> Tuple[bool, bool, bool]:
        """Determine which type of report is applicable for this action.

        Note that skipped_action is applicable if none of the other return values are true.

        Returns:
            * Whether test_suite is applicable
            * Whether test_scenario is applicable
            * Whether action_generator is applicable
        """
        test_suite = "test_suite" in self and self.test_suite is not None
        test_scenario = "test_scenario" in self and self.test_scenario is not None
        action_generator = (
            "action_generator" in self and self.action_generator is not None
        )
        skipped_action = "skipped_action" in self and self.skipped_action is not None
        if (
            sum(
                1 if case else 0
                for case in [
                    test_suite,
                    test_scenario,
                    action_generator,
                    skipped_action,
                ]
            )
            != 1
        ):
            raise ValueError(
                "Exactly one of `test_suite`, `test_scenario`, `action_generator`, or `skipped_action` must be populated"
            )
        return test_suite, test_scenario, action_generator

    def _conditional(
        self,
        test_suite_func: Union[Callable[[TestSuiteReport], Any], Callable[[Any], Any]],
        test_scenario_func: Optional[Callable[[TestScenarioReport], Any]] = None,
        action_generator_func: Optional[Callable[[ActionGeneratorReport], Any]] = None,
        skipped_action_func: Optional[Callable[[SkippedActionReport], Any]] = None,
    ) -> Any:
        test_suite, test_scenario, action_generator = self.get_applicable_report()
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
        if skipped_action_func is not None:
            return skipped_action_func(self.skipped_action)
        else:
            return test_suite_func(self.skipped_action)

    def successful(self) -> bool:
        return self._conditional(lambda report: report.successful)

    def has_critical_problem(self) -> bool:
        return self._conditional(lambda report: report.has_critical_problem())

    def all_participants(self) -> Set[ParticipantID]:
        return self._conditional(lambda report: report.all_participants())

    def query_passed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[Tuple[JSONPathExpression, PassedCheck]]:
        test_suite, test_scenario, action_generator = self.get_applicable_report()
        if test_suite:
            report = self.test_suite
            prefix = "test_suite"
        elif test_scenario:
            report = self.test_scenario
            prefix = "test_scenario"
        elif action_generator:
            report = self.action_generator
            prefix = "action_generator"
        else:
            return

        for path, pc in report.query_passed_checks(participant_id):
            yield f"{prefix}.{path}", pc

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[Tuple[JSONPathExpression, FailedCheck]]:
        test_suite, test_scenario, action_generator = self.get_applicable_report()
        if test_suite:
            report = self.test_suite
            prefix = "test_suite"
        elif test_scenario:
            report = self.test_scenario
            prefix = "test_scenario"
        elif action_generator:
            report = self.action_generator
            prefix = "action_generator"
        else:
            return

        for path, fc in report.query_failed_checks(participant_id):
            yield f"{prefix}.{path}", fc

    def queries(self) -> List[fetch.Query]:
        return self._conditional(lambda report: report.queries())

    def participant_ids(self) -> Set[ParticipantID]:
        return self._conditional(lambda report: report.participant_ids())

    @property
    def start_time(self) -> Optional[StringBasedDateTime]:
        return self._conditional(lambda report: report.start_time)

    @property
    def end_time(self) -> Optional[StringBasedDateTime]:
        return self._conditional(
            lambda report: report.end_time if "end_time" in report else None
        )


class AllConditionsEvaluationReport(ImplicitDict):
    """Result of an evaluation of AllConditions determined by whether all the subconditions are satisfied."""

    satisfied_conditions: List[ParticipantCapabilityConditionEvaluationReport]
    """All of the conditions that were satisfied (there must be at least one)."""

    unsatisfied_conditions: List[ParticipantCapabilityConditionEvaluationReport]
    """All of the conditions that were unsatisfied (if any, then this condition will not be satisfied)."""


class AnyConditionEvaluationReport(ImplicitDict):
    """Result of an evaluation of AnyCondition determined by whether any of the subconditions are satisfied."""

    satisfied_options: List[ParticipantCapabilityConditionEvaluationReport]
    """Which of the specified options were satisfied (if any were satisfied, then this condition should be satisfied)."""

    unsatisfied_options: List[ParticipantCapabilityConditionEvaluationReport]
    """Which of the specified options were not satisfied (these are informational only and do not affect the evaluation)."""


class NoFailedChecksConditionEvaluationReport(ImplicitDict):
    """Result of an evaluation of NoFailedChecksCondition dependent on whether any checks failed within the scope of the test suite in which this condition is located."""

    failed_checks: List[JSONPathExpression]
    """The location of each FailedCheck, relative to the TestSuiteReport in which this report is located."""


class CheckedRequirement(ImplicitDict):
    """A single requirement being checked for participant-verifiable capability verification."""

    requirement_id: RequirementID
    """The requirement being checked."""

    passed_checks: List[JSONPathExpression]
    """The location of each PassedCheck involving the requirement of interest, relative to the TestSuiteReport in which the RequirementsCheckedConditionEvaluationReport containing this checked requirement is located."""

    failed_checks: List[JSONPathExpression]
    """The location of each PassedCheck involving the requirement of interest, relative to the TestSuiteReport in which the RequirementsCheckedConditionEvaluationReport containing this checked requirement is located."""


class RequirementsCheckedConditionEvaluationReport(ImplicitDict):
    """Result of an evaluation of RequirementsCheckedCondition dependent on whether a set of requirements were successfully checked."""

    passed_requirements: List[CheckedRequirement]
    """Requirements with only PassedChecks."""

    failed_requirements: List[CheckedRequirement]
    """Requirements with FailedChecks."""

    untested_requirements: List[RequirementID]
    """Requirements that didn't have any PassedChecks or FailedChecks within the scope of the test suite in which this condition is located."""


class CheckedCapability(ImplicitDict):
    """Existing/previous participant-verifiable capability upon which a CapabilityVerifiedCondition depends."""

    report_location: JSONPathExpression
    """Location of the ParticipantCapabilityEvaluationReport for the existing/previous capability, relative to the TestSuiteReport in which the CapabilityVerifiedConditionEvaluationReport containing this CheckedCapability is located."""

    capability_id: CapabilityID
    """ID of the existing/previous participant-verifiable capability."""

    capability_location: JSONPathExpression
    """The location of the ParticipantCapabilityConditionEvaluationReport for the capability, relative to the TestSuiteReport in which this checked requirement is located."""

    capability_verified: bool
    """Whether this capability was successfully verified"""


class SpuriousReportMatch(ImplicitDict):
    """Participant-verifiable capability evaluations are only present in TestSuiteReports.  If a CapabilityVerifiedCondition points to a report element that is not a TestSuiteReport, an instance of this class will be generated."""

    location: JSONPathExpression
    """Location of the non-TestSuiteReport report element matching the CapabilityVerifiedCondition's `capability_location`, relative to the TestSuiteReport in which this condition is located."""

    type: str
    """Data type of the report element (not TestSuiteReport)."""


class CapabilityVerifiedConditionEvaluationReport(ImplicitDict):
    """Result of an evaluation of a CapabilityVerifiedCondition dependent on whether other capabilities were verified."""

    checked_capabilities: List[CheckedCapability]
    """All capability evaluations checked for this condition."""

    missing_capabilities: List[CapabilityID]
    """Capabilities specified for this condition but not found in the report."""

    spurious_matches: List[SpuriousReportMatch]
    """Report elements matching the condition's `capability_location`, but not of the type TestSuiteReport."""


class ParticipantCapabilityConditionEvaluationReport(ImplicitDict):
    """Result of an evaluation of a condition related to whether a participant capability should be verified.

    Exactly one field other than `condition_satisfied` must be specified."""

    condition_satisfied: bool
    """Whether the condition was satisfied for the relevant participant."""

    all_conditions: Optional[AllConditionsEvaluationReport]
    """When specified, the condition evaluated was AllConditions."""

    any_conditions: Optional[AnyConditionEvaluationReport]
    """When specified, the condition evaluated was AnyCondition."""

    no_failed_checks: Optional[NoFailedChecksConditionEvaluationReport]
    """When specified, the condition evaluated was NoFailedChecksCondition."""

    requirements_checked: Optional[RequirementsCheckedConditionEvaluationReport]
    """When specified, the condition evaluated was RequirementsCheckedCondition."""

    capability_verified: Optional[CapabilityVerifiedConditionEvaluationReport]
    """When specified, the condition evaluated was CapabilityVerifiedCondition."""


class ParticipantCapabilityEvaluationReport(ImplicitDict):
    capability_id: CapabilityID
    """ID of capability being evaluated."""

    participant_id: ParticipantID
    """ID of participant for which capability is being evaluated."""

    verified: bool
    """Whether the capability was successfully verified."""

    condition_evaluation: ParticipantCapabilityConditionEvaluationReport
    """Report produced by evaluating the condition for verifying this capability."""


class SkippedActionReport(ImplicitDict):
    timestamp: StringBasedDateTime
    """The time at which the action was skipped."""

    reason: str
    """The reason the action was skipped."""

    declaration: TestSuiteActionDeclaration
    """Full declaration of the action that was skipped."""

    @property
    def successful(self) -> bool:
        return True

    def has_critical_problem(self) -> bool:
        return False

    def all_participants(self) -> Set[ParticipantID]:
        return set()

    def queries(self) -> List[fetch.Query]:
        return []

    def participant_ids(self) -> Set[ParticipantID]:
        return set()

    @property
    def start_time(self) -> Optional[StringBasedDateTime]:
        return self.timestamp

    @property
    def end_time(self) -> Optional[StringBasedDateTime]:
        return self.timestamp


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
    """Reports from test scenarios and test suites comprising the test suite for this report, in order of execution."""

    end_time: Optional[StringBasedDateTime]
    """Time at which the test suite completed"""

    successful: bool = False
    """True iff test suite completed normally with no failed checks"""

    capability_evaluations: List[ParticipantCapabilityEvaluationReport]
    """List of capabilities defined in this test suite, evaluated for each participant."""

    def has_critical_problem(self) -> bool:
        return any(a.has_critical_problem() for a in self.actions)

    def all_participants(self) -> Set[ParticipantID]:
        participants = set()
        for action in self.actions:
            participants = participants.union(action.all_participants())
        return participants

    def query_passed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[Tuple[JSONPathExpression, PassedCheck]]:
        for i, action in enumerate(self.actions):
            for path, pc in action.query_passed_checks(participant_id):
                yield f"actions[{i}].{path}", pc

    def query_failed_checks(
        self, participant_id: Optional[str] = None
    ) -> Iterator[Tuple[JSONPathExpression, FailedCheck]]:
        for i, action in enumerate(self.actions):
            for path, fc in action.query_failed_checks(participant_id):
                yield f"actions[{i}].{path}", fc

    def queries(self) -> List[fetch.Query]:
        queries = list()
        for action in self.actions:
            queries.extend(action.queries())
        return queries

    def participant_ids(self) -> Set[ParticipantID]:
        ids = set()
        for action in self.actions:
            ids.update(action.participant_ids())
        return ids


class TestRunReport(ImplicitDict):
    codebase_version: str
    """Version of codebase used to run uss_qualifier"""

    commit_hash: str
    """Full commit hash of codebase used to run uss_qualifier"""

    baseline_signature: str
    """Signature of the test run including codebase version and all file signatures except excluded environmental files.

    This field can be used to identify that a particular expected test baseline (codebase, all non-environmental inputs)
    was run.  The value of this field is computed from codebase_version and all elements of the configuration that are
    not explicitly excluded as environmental configuration."""

    environment_signature: str
    """Signature of the environmental inputs of the configuration not included in the baseline signature."""

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
