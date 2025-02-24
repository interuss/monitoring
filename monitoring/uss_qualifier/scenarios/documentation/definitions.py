from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from implicitdict import ImplicitDict

from monitoring.monitorlib.inspection import fullname
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


class TestCheckTree(ImplicitDict):
    scenarios: Dict[str, Dict[str, Dict[str, List[str]]]]

    def add_check(
        self,
        scenario,  # TestScenarioType
        case: TestCaseDocumentation,
        step: TestStepDocumentation,
        check: TestCheckDocumentation,
    ) -> None:
        scenario_name = fullname(scenario)[len("monitoring.uss_qualifier.") :]
        self.add_check_name(scenario_name, case.name, step.name, check.name)

    def add_check_name(
        self, scenario_name: str, case_name: str, step_name: str, check_name: str
    ):
        if scenario_name not in self.scenarios:
            self.scenarios[scenario_name] = {}

        cases = self.scenarios[scenario_name]
        if case_name not in cases:
            cases[case_name] = {}

        steps = cases[case_name]
        if step_name not in steps:
            steps[step_name] = []

        checks = steps[step_name]
        checks.append(check_name)

    @property
    def n(self) -> int:
        count = 0
        for _, cases in self.scenarios.items():
            for _, steps in cases.items():
                for _, checks in steps.items():
                    count += len(checks)
        return count

    def without(self, other: TestCheckTree) -> TestCheckTree:
        result = TestCheckTree(scenarios={})
        for scenario, cases in self.scenarios.items():
            for case, steps in cases.items():
                for step, checks in steps.items():
                    for check in checks:
                        if (
                            scenario in other.scenarios
                            and case in other.scenarios[scenario]
                            and step in other.scenarios[scenario][case]
                            and check in other.scenarios[scenario][case][step]
                        ):
                            continue
                        result.add_check_name(scenario, case, step, check)
        return result

    def write(self, local_filename: str) -> None:
        json_filename = os.path.join(os.path.dirname(__file__), local_filename)
        with open(json_filename, "w") as f:
            json.dump(self, f, indent=2, sort_keys=True)

    def render(self) -> str:
        return json.dumps(self.scenarios, indent=2, sort_keys=True)

    @staticmethod
    def preexisting(local_filename: str) -> TestCheckTree:
        json_filename = os.path.join(os.path.dirname(__file__), local_filename)
        if os.path.exists(json_filename):
            with open(json_filename, "r") as f:
                return ImplicitDict.parse(json.load(f), TestCheckTree)
        else:
            return TestCheckTree(scenarios=[])
