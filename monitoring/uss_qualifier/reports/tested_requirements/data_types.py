from enum import Enum
from typing import List, Dict, Optional

from implicitdict import ImplicitDict

from monitoring.uss_qualifier.configurations.configuration import (
    ParticipantID,
)
from monitoring.uss_qualifier.requirements.definitions import PackageID
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioTypeName


PASS_CLASS = "pass_result"
NOT_TESTED_CLASS = "not_tested"
FAIL_CLASS = "fail_result"
HAS_TODO_CLASS = "has_todo"


class TestedCheck(ImplicitDict):
    name: str
    url: str
    has_todo: bool
    successes: int = 0
    failures: int = 0

    @property
    def result(self) -> str:
        if self.failures > 0:
            return "Fail"
        if self.not_tested:
            return "Not tested"
        else:
            return "Pass"

    @property
    def check_classname(self) -> str:
        if self.failures > 0:
            return FAIL_CLASS
        if self.successes + self.failures == 0:
            if self.has_todo:
                return HAS_TODO_CLASS
            else:
                return NOT_TESTED_CLASS
        else:
            return PASS_CLASS

    @property
    def result_classname(self) -> str:
        if self.failures > 0:
            return FAIL_CLASS
        if self.successes + self.failures == 0:
            return NOT_TESTED_CLASS
        else:
            return PASS_CLASS

    @property
    def not_tested(self) -> bool:
        return self.successes + self.failures == 0


class TestedStep(ImplicitDict):
    name: str
    url: str
    checks: List[TestedCheck]

    @property
    def rows(self) -> int:
        return len(self.checks)

    @property
    def no_failures(self) -> bool:
        return all(c.failures == 0 for c in self.checks)

    @property
    def not_tested(self) -> bool:
        return all(c.not_tested for c in self.checks)


class TestedCase(ImplicitDict):
    name: str
    url: str
    steps: List[TestedStep]

    @property
    def rows(self) -> int:
        return sum(s.rows for s in self.steps)

    @property
    def no_failures(self) -> bool:
        return all(s.no_failures for s in self.steps)

    @property
    def not_tested(self) -> bool:
        return all(s.not_tested for s in self.steps)


class TestedScenario(ImplicitDict):
    type: TestScenarioTypeName
    name: str
    url: str
    cases: List[TestedCase]

    @property
    def rows(self) -> int:
        return sum(c.rows for c in self.cases)

    @property
    def no_failures(self) -> bool:
        return all(c.no_failures for c in self.cases)

    @property
    def not_tested(self) -> bool:
        return all(c.not_tested for c in self.cases)


class TestedRequirement(ImplicitDict):
    id: str
    scenarios: List[TestedScenario]

    @property
    def rows(self) -> int:
        n = sum(s.rows for s in self.scenarios)
        if n == 0:
            n = 1
        return n

    @property
    def classname(self) -> str:
        if not all(s.no_failures for s in self.scenarios):
            return FAIL_CLASS
        elif all(s.not_tested for s in self.scenarios):
            return NOT_TESTED_CLASS
        else:
            return PASS_CLASS


class TestedPackage(ImplicitDict):
    id: PackageID
    url: str
    name: str
    requirements: List[TestedRequirement]

    @property
    def rows(self) -> int:
        return sum(r.rows for r in self.requirements)


class TestedBreakdown(ImplicitDict):
    packages: List[TestedPackage]


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

    Fail = "Fail"
    """Participant has failed to comply with one or more requirements."""

    Incomplete = "Incomplete"
    """Participant has not failed to comply with any requirements, but some identified requirements were not verified."""

    def get_class(self) -> str:
        if self == ParticipantVerificationStatus.Pass:
            return PASS_CLASS
        elif self == ParticipantVerificationStatus.Fail:
            return FAIL_CLASS
        elif self == ParticipantVerificationStatus.Incomplete:
            return NOT_TESTED_CLASS
        else:
            return ""


class ParticipantVerificationInfo(ImplicitDict):
    status: ParticipantVerificationStatus
    """Verification status of participant for the associated requirements set."""

    system_version: Optional[str] = None
    """The version of the participant's system that was tested, if this information was acquired during testing."""


class RequirementsVerificationReport(ImplicitDict):
    test_run_information: TestRunInformation
    """Information about the test run during which the participant_verifications were determined."""

    participant_verifications: Dict[ParticipantID, ParticipantVerificationInfo]
    """Information regarding verification of compliance for each participant."""

    artifact_configuration: Optional[str]
    """Name of the tested requirements artifact configuration from the test run configuration, or "post-hoc" if the
    artifact configuration generating this verification report is not specified in the test run configuration."""
