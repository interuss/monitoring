from typing import Iterable, List, Optional, Set, Tuple, Union

from implicitdict import ImplicitDict

from monitoring.monitorlib.versioning import repo_url_of
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_generator_definition,
)
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.reports.report import (
    FailedCheck,
    PassedCheck,
    TestCaseReport,
    TestRunReport,
    TestScenarioReport,
    TestStepReport,
    TestSuiteActionReport,
)
from monitoring.uss_qualifier.reports.tested_requirements.data_types import (
    TestedBreakdown,
    TestedCase,
    TestedCheck,
    TestedPackage,
    TestedRequirement,
    TestedScenario,
    TestedStep,
)
from monitoring.uss_qualifier.reports.tested_requirements.sorting import sort_breakdown
from monitoring.uss_qualifier.requirements.definitions import RequirementID
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioTypeName
from monitoring.uss_qualifier.scenarios.documentation.parsing import get_documentation
from monitoring.uss_qualifier.scenarios.scenario import get_scenario_type_by_name
from monitoring.uss_qualifier.suites.definitions import (
    ActionType,
    TestSuiteActionDeclaration,
    TestSuiteDefinition,
)


def make_breakdown(
    report: TestRunReport,
    participant_reqs: Optional[Set[RequirementID]],
    participant_ids: Iterable[ParticipantID],
) -> TestedBreakdown:
    """Break down a report into requirements tested for the specified participants.

    Args:
        report: Report to break down.
        participant_reqs: Set of requirements to report for these participants.  If None, defaults to everything.
        participant_ids: IDs of participants for which the breakdown is being computed.

    Returns: TestedBreakdown for participants for report.
    """
    participant_breakdown = TestedBreakdown(packages=[])
    _populate_breakdown_with_action_report(
        participant_breakdown, report.report, participant_ids, participant_reqs
    )
    _populate_breakdown_with_action_declaration(
        participant_breakdown, report.configuration.v1.test_run.action, participant_reqs
    )
    if participant_reqs is not None:
        _populate_breakdown_with_req_set(participant_breakdown, participant_reqs)
    sort_breakdown(participant_breakdown)
    return participant_breakdown


def _populate_breakdown_with_req_set(
    breakdown: TestedBreakdown, req_set: Set[RequirementID]
) -> None:
    for req_id in req_set:
        package_id = req_id.package()
        matches = [p for p in breakdown.packages if p.id == package_id]
        if matches:
            tested_package = matches[0]
        else:
            url = repo_url_of(package_id.md_file_path())
            tested_package = TestedPackage(
                id=package_id, url=url, name=package_id, requirements=[]
            )
            breakdown.packages.append(tested_package)

        short_req_id = req_id.split(".")[-1]
        matches = [r for r in tested_package.requirements if r.id == short_req_id]
        if matches:
            tested_requirement = matches[0]
        else:
            tested_requirement = TestedRequirement(id=short_req_id, scenarios=[])
            tested_package.requirements.append(tested_requirement)


def _populate_breakdown_with_action_report(
    breakdown: TestedBreakdown,
    action: TestSuiteActionReport,
    participant_ids: Iterable[ParticipantID],
    req_set: Optional[Set[RequirementID]],
) -> None:
    test_suite, test_scenario, action_generator = action.get_applicable_report()
    if test_scenario:
        return _populate_breakdown_with_scenario_report(
            breakdown, action.test_scenario, participant_ids, req_set
        )
    elif test_suite:
        for subaction in action.test_suite.actions:
            _populate_breakdown_with_action_report(
                breakdown, subaction, participant_ids, req_set
            )
    elif action_generator:
        for subaction in action.action_generator.actions:
            _populate_breakdown_with_action_report(
                breakdown, subaction, participant_ids, req_set
            )
    else:
        pass  # Skipped action


def _populate_breakdown_with_scenario_report(
    breakdown: TestedBreakdown,
    scenario_report: TestScenarioReport,
    participant_ids: Iterable[ParticipantID],
    req_set: Optional[Set[RequirementID]],
) -> None:
    scenario_type_name = scenario_report.scenario_type
    steps: List[Tuple[Optional[TestCaseReport], TestStepReport]] = []
    for case in scenario_report.cases:
        for step in case.steps:
            steps.append((case, step))
    if "cleanup" in scenario_report and scenario_report.cleanup:
        steps.append((None, scenario_report.cleanup))

    for case, step in steps:
        for check in step.passed_checks + step.failed_checks:
            if not any(pid in check.participants for pid in participant_ids):
                continue
            for req_id in check.requirements:
                if req_set is not None and req_id not in req_set:
                    continue
                package_id = req_id.package()
                package_name = "<br>.".join(package_id.split("."))
                matches = [p for p in breakdown.packages if p.id == package_id]
                if matches:
                    tested_package = matches[0]
                else:
                    # TODO: Improve name of package by using title of page
                    url = repo_url_of(package_id.md_file_path())
                    tested_package = TestedPackage(
                        id=package_id, url=url, name=package_name, requirements=[]
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

                if case:
                    case_name = case.name
                    case_url = case.documentation_url
                else:
                    case_name = "Cleanup"
                    case_url = step.documentation_url
                matches = [c for c in tested_scenario.cases if c.name == case_name]
                if matches:
                    tested_case = matches[0]
                else:
                    tested_case = TestedCase(name=case_name, url=case_url, steps=[])
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
                    tested_check = TestedCheck(
                        name=check.name, url="", has_todo=False
                    )  # TODO: Consider populating has_todo with documentation instead
                    if isinstance(check, FailedCheck):
                        tested_check.url = check.documentation_url
                    tested_step.checks.append(tested_check)
                if isinstance(check, PassedCheck):
                    tested_check.successes += 1
                elif isinstance(check, FailedCheck):
                    if check.severity == Severity.Low:
                        tested_check.findings += 1
                    else:
                        tested_check.failures += 1
                else:
                    raise ValueError("Check is neither PassedCheck nor FailedCheck")


def _populate_breakdown_with_action_declaration(
    breakdown: TestedBreakdown,
    action: Union[TestSuiteActionDeclaration, PotentialGeneratedAction],
    req_set: Optional[Set[RequirementID]],
) -> None:
    action_type = action.get_action_type()
    if action_type == ActionType.TestScenario:
        _populate_breakdown_with_scenario(
            breakdown, action.test_scenario.scenario_type, req_set
        )
    elif action_type == ActionType.TestSuite:
        if "suite_type" in action.test_suite and action.test_suite.suite_type:
            suite_def: TestSuiteDefinition = ImplicitDict.parse(
                load_dict_with_references(action.test_suite.suite_type),
                TestSuiteDefinition,
            )
            for a in suite_def.actions:
                _populate_breakdown_with_action_declaration(breakdown, a, req_set)
        elif (
            "suite_definition" in action.test_suite
            and action.test_suite.suite_definition
        ):
            for a in action.test_suite.suite_definition.actions:
                _populate_breakdown_with_action_declaration(breakdown, a, req_set)
        else:
            raise ValueError(f"Test suite action missing suite type or definition")
    elif action_type == ActionType.ActionGenerator:
        potential_actions = list_potential_actions_for_action_generator_definition(
            action.action_generator
        )
        for a in potential_actions:
            _populate_breakdown_with_action_declaration(breakdown, a, req_set)
    else:
        raise NotImplementedError(f"Unsupported test suite action type: {action_type}")


def _populate_breakdown_with_scenario(
    breakdown: TestedBreakdown,
    scenario_type_name: TestScenarioTypeName,
    req_set: Optional[Set[RequirementID]],
) -> None:
    scenario_type = get_scenario_type_by_name(scenario_type_name)
    scenario_doc = get_documentation(scenario_type)
    for case in scenario_doc.cases:
        for step in case.steps:
            for check in step.checks:
                for req_id in check.applicable_requirements:
                    if req_set is not None and req_id not in req_set:
                        continue
                    package_id = req_id.package()
                    package_name = "<br>.".join(package_id.split("."))
                    matches = [p for p in breakdown.packages if p.id == package_id]
                    if matches:
                        tested_package = matches[0]
                    else:
                        # TODO: Improve name of package by using title of page
                        url = repo_url_of(package_id.md_file_path())
                        tested_package = TestedPackage(
                            id=package_id, url=url, name=package_name, requirements=[]
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
                        tested_check = TestedCheck(
                            name=check.name, url=check.url, has_todo=check.has_todo
                        )
                        tested_step.checks.append(tested_check)
                    if not tested_check.url:
                        tested_check.url = check.url
