from implicitdict import ImplicitDict

from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.reports.report import RequirementID


class TestCheckDocumentation(ImplicitDict):
    name: str
    url: str | None = None
    applicable_requirements: list[RequirementID]
    has_todo: bool
    severity: Severity | None = None


class TestStepDocumentation(ImplicitDict):
    name: str
    url: str | None = None
    checks: list[TestCheckDocumentation]


class TestCaseDocumentation(ImplicitDict):
    name: str
    url: str | None = None
    steps: list[TestStepDocumentation]

    def get_step_by_name(self, step_name: str) -> TestStepDocumentation | None:
        for step in self.steps:
            if step.name == step_name:
                return step
        return None


class TestScenarioDocumentation(ImplicitDict):
    name: str
    url: str | None = None
    local_path: str
    resources: list[str] | None
    cases: list[TestCaseDocumentation]
    cleanup: TestStepDocumentation | None

    def get_case_by_name(self, case_name: str) -> TestCaseDocumentation | None:
        for case in self.cases:
            if case.name == case_name:
                return case
        return None
