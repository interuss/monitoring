from typing import Optional, List

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.reports.report import RequirementID


class TestCheckDocumentation(ImplicitDict):
    name: str
    url: Optional[str] = None
    applicable_requirements: List[RequirementID]
    has_todo: bool
    severity: Optional[Severity] = None


class TestStepDocumentation(ImplicitDict):
    name: str
    url: Optional[str] = None
    checks: List[TestCheckDocumentation]


class TestCaseDocumentation(ImplicitDict):
    name: str
    url: Optional[str] = None
    steps: List[TestStepDocumentation]

    def get_step_by_name(self, step_name: str) -> Optional[TestStepDocumentation]:
        for step in self.steps:
            if step.name == step_name:
                return step
        return None


class TestScenarioDocumentation(ImplicitDict):
    name: str
    url: Optional[str] = None
    local_path: str
    resources: Optional[List[str]]
    cases: List[TestCaseDocumentation]
    cleanup: Optional[TestStepDocumentation]

    def get_case_by_name(self, case_name: str) -> Optional[TestCaseDocumentation]:
        for case in self.cases:
            if case.name == case_name:
                return case
        return None
