from collections.abc import Iterable
from enum import Enum

from implicitdict import ImplicitDict, Optional

from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.requirements.definitions import PackageID
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioTypeName

PASS_CLASS = "pass_result"
FINDINGS_CLASS = "findings_result"
NOT_TESTED_CLASS = "not_tested"
FAIL_CLASS = "fail_result"
ACCEPTED_FINDINGS_CLASS = "accepted_findings_result"
HAS_TODO_CLASS = "has_todo"


class TestedCheck(ImplicitDict):
    name: str
    url: str
    has_todo: bool
    is_finding_acceptable: bool
    successes: int = 0
    findings: int = 0
    failures: int = 0

    @property
    def result(self) -> str:
        if self.failures > 0:
            return "Fail"
        if self.findings > 0 and self.successes == 0:
            return "Findings"
        if self.findings == 0 and self.successes > 0:
            return "Pass"
        if self.findings > 0 and self.successes > 0:
            return "Pass (with findings)"
        return "Not tested"

    @property
    def check_classname(self) -> str:
        if self.failures > 0:
            return ACCEPTED_FINDINGS_CLASS if self.is_finding_acceptable else FAIL_CLASS
        if self.successes + self.failures == 0:
            if self.has_todo:
                return HAS_TODO_CLASS
            else:
                return NOT_TESTED_CLASS
        else:
            return PASS_CLASS

    @property
    def result_classname(self) -> str:
        if self.is_finding_acceptable:
            if self.successes > 0:
                return PASS_CLASS
            elif self.failures > 0 or self.findings > 0:
                return ACCEPTED_FINDINGS_CLASS
            else:
                return NOT_TESTED_CLASS
        else:
            if self.failures > 0:
                return FAIL_CLASS
            if self.successes + self.failures + self.findings == 0:
                return NOT_TESTED_CLASS
            if self.findings > 0:
                return FINDINGS_CLASS
            return PASS_CLASS


class TestedStep(ImplicitDict):
    name: str
    url: str
    checks: list[TestedCheck]

    @property
    def rows(self) -> int:
        return len(self.checks)


class TestedCase(ImplicitDict):
    name: str
    url: str
    steps: list[TestedStep]

    @property
    def rows(self) -> int:
        return sum(s.rows for s in self.steps)


class TestedScenario(ImplicitDict):
    type: TestScenarioTypeName
    name: str
    url: str
    cases: list[TestedCase]

    @property
    def rows(self) -> int:
        return sum(c.rows for c in self.cases)


class TestedRequirementStatus(str, Enum):
    Pass = "Pass"
    PassWithFindings = "Pass (with findings)"
    Findings = "Findings"
    Fail = "Fail"
    NotTested = "Not tested"


class TestedRequirement(ImplicitDict):
    id: str
    scenarios: list[TestedScenario]

    @property
    def rows(self) -> int:
        n = sum(s.rows for s in self.scenarios)
        if n == 0:
            n = 1
        return n

    @property
    def checks(self) -> Iterable[TestedCheck]:
        for scenario in self.scenarios:
            for case in scenario.cases:
                for step in case.steps:
                    yield from step.checks

    @property
    def status(self) -> TestedRequirementStatus:
        if any((c.failures > 0 and not c.is_finding_acceptable) for c in self.checks):
            return TestedRequirementStatus.Fail
        if all(c.successes == 0 for c in self.checks) and any(
            c.findings > 0 for c in self.checks
        ):
            return TestedRequirementStatus.Findings
        if any(c.successes > 0 for c in self.checks) and any(
            (c.findings > 0 and not c.is_finding_acceptable) for c in self.checks
        ):
            return TestedRequirementStatus.PassWithFindings
        if any(c.successes > 0 for c in self.checks):
            return TestedRequirementStatus.Pass
        return TestedRequirementStatus.NotTested

    @property
    def classname(self) -> str:
        return {
            TestedRequirementStatus.Fail: FAIL_CLASS,
            TestedRequirementStatus.Findings: FINDINGS_CLASS,
            TestedRequirementStatus.PassWithFindings: FINDINGS_CLASS,
            TestedRequirementStatus.Pass: PASS_CLASS,
            TestedRequirementStatus.NotTested: NOT_TESTED_CLASS,
        }[self.status]


class TestedPackage(ImplicitDict):
    id: PackageID
    url: str
    name: str
    requirements: list[TestedRequirement]

    @property
    def rows(self) -> int:
        return sum(r.rows for r in self.requirements)


class TestedBreakdown(ImplicitDict):
    packages: list[TestedPackage]


class TestRunInformation(ImplicitDict):
    test_run_id: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    baseline: str
    environment: str


class ParticipantVerificationStatus(str, Enum):
    Unknown = "Unknown"
    """Participant verification status is not known."""

    Pass = "Pass"
    """Participant has verified all tested requirements."""

    PassWithFindings = "PassWithFindings"
    """Participant has verified all tested requirements, but has some additional findings."""

    Fail = "Fail"
    """Participant has failed to comply with one or more requirements."""

    NotFullyVerified = "NotFullyVerified"
    """Participant has not failed to comply with any requirements, but some identified requirements were not verified."""

    def get_class(self) -> str:
        if self == ParticipantVerificationStatus.Pass:
            return PASS_CLASS
        elif self == ParticipantVerificationStatus.PassWithFindings:
            return PASS_CLASS
        elif self == ParticipantVerificationStatus.Fail:
            return FAIL_CLASS
        elif self == ParticipantVerificationStatus.NotFullyVerified:
            return NOT_TESTED_CLASS
        else:
            return ""

    def get_text(self) -> str:
        if self == ParticipantVerificationStatus.Pass:
            return "Pass"
        elif self == ParticipantVerificationStatus.PassWithFindings:
            return "Pass (with findings)"
        elif self == ParticipantVerificationStatus.Fail:
            return "Fail"
        elif self == ParticipantVerificationStatus.NotFullyVerified:
            return "Not fully verified"
        else:
            return "???"


class ParticipantVerificationInfo(ImplicitDict):
    status: ParticipantVerificationStatus
    """Verification status of participant for the associated requirements set."""

    system_version: Optional[str] = None
    """The version of the participant's system that was tested, if this information was acquired during testing."""


class RequirementsVerificationReport(ImplicitDict):
    test_run_information: TestRunInformation
    """Information about the test run during which the participant_verifications were determined."""

    participant_verifications: dict[ParticipantID, ParticipantVerificationInfo]
    """Information regarding verification of compliance for each participant."""

    artifact_configuration: Optional[str]
    """Name of the tested requirements artifact configuration from the test run configuration, or "post-hoc" if the
    artifact configuration generating this verification report is not specified in the test run configuration."""
