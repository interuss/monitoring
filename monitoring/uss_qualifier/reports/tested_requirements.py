import os
import shutil
from typing import List, Union

from implicitdict import ImplicitDict
from monitoring.monitorlib.inspection import import_submodules
from monitoring.uss_qualifier import scenarios, suites, action_generators
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_generator_definition,
)
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.reports import jinja_env
from monitoring.uss_qualifier.reports.report import (
    TestRunReport,
    TestSuiteActionReport,
    TestScenarioReport,
    PassedCheck,
    FailedCheck,
)
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioTypeName
from monitoring.uss_qualifier.scenarios.documentation.parsing import get_documentation
from monitoring.uss_qualifier.scenarios.scenario import get_scenario_type_by_name
from monitoring.uss_qualifier.suites.definitions import (
    TestSuiteActionDeclaration,
    ActionType,
    TestSuiteDefinition,
)


class TestedCheck(ImplicitDict):
    name: str
    url: str
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
    def classname(self) -> str:
        if self.failures > 0:
            return "fail_result"
        if self.successes + self.failures == 0:
            return "not_tested"
        else:
            return "pass_result"

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
        return sum(s.rows for s in self.scenarios)

    @property
    def classname(self) -> str:
        if not all(s.no_failures for s in self.scenarios):
            return "fail_result"
        elif all(s.not_tested for s in self.scenarios):
            return "not_tested"
        else:
            return "pass_result"


class TestedPackage(ImplicitDict):
    id: str
    name: str
    requirements: List[TestedRequirement]

    @property
    def rows(self) -> int:
        return sum(r.rows for r in self.requirements)


class TestedBreakdown(ImplicitDict):
    packages: List[TestedPackage]


def generate_tested_requirements(report: TestRunReport, output_path: str) -> None:
    import_submodules(scenarios)
    import_submodules(suites)
    import_submodules(action_generators)

    os.makedirs(output_path, exist_ok=True)
    index_file = os.path.join(output_path, "index.html")

    participant_ids = report.report.participant_ids()
    template = jinja_env.get_template("tested_requirements/test_run_report.html")
    with open(index_file, "w") as f:
        f.write(template.render(participant_ids=participant_ids))

    template = jinja_env.get_template(
        "tested_requirements/participant_tested_requirements.html"
    )
    for participant_id in participant_ids:
        participant_breakdown = TestedBreakdown(packages=[])
        _populate_breakdown_with_action_report(
            participant_breakdown, report.report, participant_id
        )
        _populate_breakdown_with_action_declaration(
            participant_breakdown, report.configuration.action
        )
        _sort_breakdown(participant_breakdown)
        participant_file = os.path.join(output_path, f"{participant_id}.html")
        with open(participant_file, "w") as f:
            f.write(
                template.render(
                    participant_id=participant_id, breakdown=participant_breakdown
                )
            )


def _sort_breakdown(breakdown: TestedBreakdown) -> None:
    breakdown.packages.sort(key=lambda p: p.id)
    for package in breakdown.packages:
        package.requirements.sort(key=lambda r: r.id)
        for requirement in package.requirements:
            requirement.scenarios.sort(key=lambda s: s.name)


def _populate_breakdown_with_action_report(
    breakdown: TestedBreakdown,
    action: TestSuiteActionReport,
    participant_id: ParticipantID,
) -> None:
    test_suite, test_scenario, action_generator = action.get_applicable_report()
    if test_scenario:
        return _populate_breakdown_with_scenario_report(
            breakdown, action.test_scenario, participant_id
        )
    elif test_suite:
        for subaction in action.test_suite.actions:
            _populate_breakdown_with_action_report(breakdown, subaction, participant_id)
    elif action_generator:
        for subaction in action.action_generator.actions:
            _populate_breakdown_with_action_report(breakdown, subaction, participant_id)
    else:
        raise ValueError(f"Unsupported test suite report type")


def _populate_breakdown_with_scenario_report(
    breakdown: TestedBreakdown,
    scenario_report: TestScenarioReport,
    participant_id: ParticipantID,
) -> None:
    scenario_type_name = scenario_report.scenario_type
    for case in scenario_report.cases:
        for step in case.steps:
            for check in step.passed_checks + step.failed_checks:
                if participant_id not in check.participants:
                    continue
                for req_id in check.requirements:
                    package_id = ".".join(req_id.split(".")[0:-1])
                    package_name = "<br>.".join(package_id.split("."))
                    matches = [p for p in breakdown.packages if p.id == package_id]
                    if matches:
                        tested_package = matches[0]
                    else:
                        # TODO: Improve name of package by using title of page
                        tested_package = TestedPackage(
                            id=package_id, name=package_name, requirements=[]
                        )
                        breakdown.packages.append(tested_package)

                    short_req_id = req_id.split(".")[-1]
                    matches = [
                        r for r in tested_package.requirements if r.id == short_req_id
                    ]
                    if matches:
                        tested_requirement = matches[0]
                    else:
                        tested_requirement = TestedRequirement(
                            id=short_req_id, scenarios=[]
                        )
                        tested_package.requirements.append(tested_requirement)

                    matches = [
                        s
                        for s in tested_requirement.scenarios
                        if s.type == scenario_type_name
                    ]
                    if matches:
                        tested_scenario = matches[0]
                    else:
                        tested_scenario = TestedScenario(
                            type=scenario_type_name,
                            name=scenario_report.name,
                            url=scenario_report.documentation_url,
                            cases=[],
                        )
                        tested_requirement.scenarios.append(tested_scenario)

                    matches = [c for c in tested_scenario.cases if c.name == case.name]
                    if matches:
                        tested_case = matches[0]
                    else:
                        tested_case = TestedCase(
                            name=case.name, url=case.documentation_url, steps=[]
                        )
                        tested_scenario.cases.append(tested_case)

                    matches = [s for s in tested_case.steps if s.name == step.name]
                    if matches:
                        tested_step = matches[0]
                    else:
                        tested_step = TestedStep(
                            name=step.name, url=step.documentation_url, checks=[]
                        )
                        tested_case.steps.append(tested_step)

                    matches = [c for c in tested_step.checks if c.name == check.name]
                    if matches:
                        tested_check = matches[0]
                    else:
                        tested_check = TestedCheck(name=check.name, url="")
                        if isinstance(check, FailedCheck):
                            tested_check.url = check.documentation_url
                        tested_step.checks.append(tested_check)
                    if isinstance(check, PassedCheck):
                        tested_check.successes += 1
                    elif isinstance(check, FailedCheck):
                        tested_check.failures += 1
                    else:
                        raise ValueError("Check is neither PassedCheck nor FailedCheck")


def _populate_breakdown_with_action_declaration(
    breakdown: TestedBreakdown,
    action: Union[TestSuiteActionDeclaration, PotentialGeneratedAction],
) -> None:
    action_type = action.get_action_type()
    if action_type == ActionType.TestScenario:
        _populate_breakdown_with_scenario(breakdown, action.test_scenario.scenario_type)
    elif action_type == ActionType.TestSuite:
        if "suite_type" in action.test_suite and action.test_suite.suite_type:
            suite_def: TestSuiteDefinition = ImplicitDict.parse(
                load_dict_with_references(action.test_suite.suite_type),
                TestSuiteDefinition,
            )
            for action in suite_def.actions:
                _populate_breakdown_with_action_declaration(breakdown, action)
        elif (
            "suite_definition" in action.test_suite
            and action.test_suite.suite_definition
        ):
            for action in action.test_suite.suite_definition:
                _populate_breakdown_with_action_declaration(breakdown, action)
        else:
            raise ValueError(f"Test suite action missing suite type or definition")
    elif action_type == ActionType.ActionGenerator:
        potential_actions = list_potential_actions_for_action_generator_definition(
            action.action_generator
        )
        for action in potential_actions:
            _populate_breakdown_with_action_declaration(breakdown, action)
    else:
        raise NotImplementedError(f"Unsupported test suite action type: {action_type}")


def _populate_breakdown_with_scenario(
    breakdown: TestedBreakdown, scenario_type_name: TestScenarioTypeName
) -> None:
    scenario_type = get_scenario_type_by_name(scenario_type_name)
    scenario_doc = get_documentation(scenario_type)
    for case in scenario_doc.cases:
        for step in case.steps:
            for check in step.checks:
                for req_id in check.applicable_requirements:
                    package_id = ".".join(req_id.split(".")[0:-1])
                    package_name = "<br>.".join(package_id.split("."))
                    matches = [p for p in breakdown.packages if p.id == package_id]
                    if matches:
                        tested_package = matches[0]
                    else:
                        # TODO: Improve name of package by using title of page
                        tested_package = TestedPackage(
                            id=package_id, name=package_name, requirements=[]
                        )
                        breakdown.packages.append(tested_package)

                    short_req_id = req_id.split(".")[-1]
                    matches = [
                        r for r in tested_package.requirements if r.id == short_req_id
                    ]
                    if matches:
                        tested_requirement = matches[0]
                    else:
                        tested_requirement = TestedRequirement(
                            id=short_req_id, scenarios=[]
                        )
                        tested_package.requirements.append(tested_requirement)

                    matches = [
                        s
                        for s in tested_requirement.scenarios
                        if s.type == scenario_type_name
                    ]
                    if matches:
                        tested_scenario = matches[0]
                    else:
                        tested_scenario = TestedScenario(
                            type=scenario_type_name,
                            name=scenario_doc.name,
                            url=scenario_doc.url,
                            cases=[],
                        )
                        tested_requirement.scenarios.append(tested_scenario)

                    matches = [c for c in tested_scenario.cases if c.name == case.name]
                    if matches:
                        tested_case = matches[0]
                    else:
                        tested_case = TestedCase(name=case.name, url=case.url, steps=[])
                        tested_scenario.cases.append(tested_case)

                    matches = [s for s in tested_case.steps if s.name == step.name]
                    if matches:
                        tested_step = matches[0]
                    else:
                        tested_step = TestedStep(
                            name=step.name, url=step.url, checks=[]
                        )
                        tested_case.steps.append(tested_step)

                    matches = [c for c in tested_step.checks if c.name == check.name]
                    if matches:
                        tested_check = matches[0]
                    else:
                        tested_check = TestedCheck(name=check.name, url=check.url)
                        if not check.has_todo:
                            tested_step.checks.append(tested_check)
                    if not tested_check.url:
                        tested_check.url = check.url
