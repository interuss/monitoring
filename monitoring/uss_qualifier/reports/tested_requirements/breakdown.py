from collections.abc import Iterable

from implicitdict import ImplicitDict

from monitoring.monitorlib.versioning import repo_url_of
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_generator_definition,
)
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import (
    FullyQualifiedCheck,
    ParticipantID,
)
from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.reports.report import (
    FailedCheck,
    PassedCheck,
    SkippedActionReport,
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
from monitoring.uss_qualifier.scenarios.scenario import (
    are_scenario_types_equal,
    fully_qualified_check_in_collection,
    get_scenario_type_by_name,
)
from monitoring.uss_qualifier.suites.definitions import (
    ActionType,
    TestSuiteActionDeclaration,
    TestSuiteDefinition,
)
from monitoring.uss_qualifier.suites.suite import TEST_RUN_TIMEOUT_SKIP_REASON

REQ_RUN_TO_COMPLETION = RequirementID(
    "interuss.automated_testing.execution.RunToCompletion"
)


def make_breakdown(
    report: TestRunReport,
    acceptable_findings: list[FullyQualifiedCheck],
    participant_reqs: set[RequirementID] | None,
    participant_ids: Iterable[ParticipantID],
) -> TestedBreakdown:
    """Break down a report into requirements tested for the specified participants.

    Args:
        report: Report to break down.
        acceptable_findings: Checks where failure is acceptable, according to the configuration.
        participant_reqs: Set of requirements to report for these participants.  If None, defaults to everything.
        participant_ids: IDs of participants for which the breakdown is being computed.

    Returns: TestedBreakdown for participants for report.
    """
    participant_breakdown = TestedBreakdown(packages=[])
    _populate_breakdown_with_action_report(
        participant_breakdown,
        report.report,
        acceptable_findings,
        participant_ids,
        participant_reqs,
    )
    assert report.configuration.v1
    assert report.configuration.v1.test_run
    _populate_breakdown_with_action_declaration(
        participant_breakdown,
        report.configuration.v1.test_run.action,
        acceptable_findings,
        participant_reqs,
    )
    if participant_reqs is not None:
        _populate_breakdown_with_req_set(participant_breakdown, participant_reqs)
        if REQ_RUN_TO_COMPLETION in participant_reqs:
            # Add a success to REQ_RUN_TO_COMPLETION if nothing caused it to fail
            tested_requirement = _tested_requirement_for(
                REQ_RUN_TO_COMPLETION, participant_breakdown
            )
            if not tested_requirement.scenarios:
                tested_requirement.scenarios.append(
                    TestedScenario(
                        type="uss_qualifier.execution",
                        name="N/A",
                        url="",
                        cases=[
                            TestedCase(
                                name="N/A",
                                url="",
                                steps=[
                                    TestedStep(
                                        name="N/A",
                                        url="",
                                        checks=[
                                            TestedCheck(
                                                name="Test run completed normally",
                                                url="",
                                                has_todo=False,
                                                is_finding_acceptable=False,
                                                successes=1,
                                            )
                                        ],
                                    )
                                ],
                            )
                        ],
                    )
                )
    sort_breakdown(participant_breakdown)
    return participant_breakdown


def _populate_breakdown_with_req_set(
    breakdown: TestedBreakdown, req_set: set[RequirementID]
) -> None:
    for req_id in req_set:
        _tested_requirement_for(req_id, breakdown)


def _populate_breakdown_with_action_report(
    breakdown: TestedBreakdown,
    action: TestSuiteActionReport,
    acceptable_findings: list[FullyQualifiedCheck],
    participant_ids: Iterable[ParticipantID],
    req_set: set[RequirementID] | None,
) -> None:
    if "test_scenario" in action and action.test_scenario:
        return _populate_breakdown_with_scenario_report(
            breakdown,
            action.test_scenario,
            acceptable_findings,
            participant_ids,
            req_set,
        )
    elif "test_suite" in action and action.test_suite:
        for subaction in action.test_suite.actions:
            _populate_breakdown_with_action_report(
                breakdown, subaction, acceptable_findings, participant_ids, req_set
            )
    elif "action_generator" in action and action.action_generator:
        for subaction in action.action_generator.actions:
            _populate_breakdown_with_action_report(
                breakdown, subaction, acceptable_findings, participant_ids, req_set
            )
    elif "skipped_action" in action and action.skipped_action:
        if (
            req_set is not None
            and REQ_RUN_TO_COMPLETION in req_set
            and action.skipped_action.reason == TEST_RUN_TIMEOUT_SKIP_REASON
        ):
            _populate_breakdown_with_timeout_skip(breakdown, action.skipped_action)
    else:
        raise ValueError(
            "Unrecognized or unspecified oneof option in TestSuiteActionReport"
        )


def _populate_breakdown_with_timeout_skip(
    breakdown: TestedBreakdown, skipped_action: SkippedActionReport
) -> None:
    declaration = skipped_action.declaration
    if "test_scenario" in declaration and declaration.test_scenario:
        doc = get_documentation(
            get_scenario_type_by_name(declaration.test_scenario.scenario_type)
        )
        default_scenario = TestedScenario(
            type=declaration.test_scenario.scenario_type,
            name=doc.name,
            documentation_url=doc.url,
            cases=[],
        )
    elif "test_suite" in declaration and declaration.test_suite:
        type_name = declaration.test_suite.type_name
        default_scenario = TestedScenario(
            name=f"(Test suite) {type_name}", type=type_name, url="", cases=[]
        )
    elif "action_generator" in declaration and declaration.action_generator:
        type_name = declaration.action_generator.generator_type
        default_scenario = TestedScenario(
            name=f"(Action generator) {type_name}", type=type_name, url="", cases=[]
        )
    else:
        raise ValueError(
            "Unrecognized or unspecified oneof option in TestSuiteActionDeclaration"
        )
    tested_requirement = _tested_requirement_for(REQ_RUN_TO_COMPLETION, breakdown)
    tested_scenario = _tested_scenario_for(default_scenario, tested_requirement)
    # Assume each TestedScenario for the TestedRequirement for this requirement should only ever have 1 case with 1 step with 1 check
    if not tested_scenario.cases:
        tested_scenario.cases.append(
            TestedCase(
                name="N/A",
                url="",
                steps=[
                    TestedStep(
                        name="N/A",
                        url="",
                        checks=[
                            TestedCheck(
                                name="Test run completed normally",
                                url="",
                                has_todo=False,
                                is_finding_acceptable=False,
                                failures=1,
                            )
                        ],
                    )
                ],
            )
        )
    else:
        if len(tested_scenario.cases) > 1:
            raise ValueError(
                f"TestedScenario {tested_scenario.name} ({tested_scenario.type}) for requirement {tested_requirement.id} was expected to only have one N/A case, but instead had {len(tested_scenario.cases)} cases: {', '.join(c.name for c in tested_scenario.cases)}"
            )
        tested_scenario.cases[0].steps[0].checks[0].failures += 1


def _populate_breakdown_with_scenario_report(
    breakdown: TestedBreakdown,
    scenario_report: TestScenarioReport,
    acceptable_findings: list[FullyQualifiedCheck],
    participant_ids: Iterable[ParticipantID],
    req_set: set[RequirementID] | None,
) -> None:
    steps: list[tuple[TestCaseReport | None, TestStepReport]] = []
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
                if req_set is None or req_id in req_set:
                    _add_check_to_breakdown_for_req(
                        req_id,
                        scenario_report,
                        case,
                        step,
                        check,
                        breakdown,
                        acceptable_findings,
                    )
            if (
                req_set is not None
                and REQ_RUN_TO_COMPLETION in req_set
                and "severity" in check
                and check.severity == Severity.Critical
            ):
                _add_check_to_breakdown_for_req(
                    REQ_RUN_TO_COMPLETION,
                    scenario_report,
                    case,
                    step,
                    check,
                    breakdown,
                    acceptable_findings,
                )


def _tested_requirement_for(
    req_id: RequirementID, breakdown: TestedBreakdown
) -> TestedRequirement:
    """Retrieves the TestedRequirement for the specified ID in the breakdown, creating an empty one if necessary."""
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
    matches = [r for r in tested_package.requirements if r.id == short_req_id]
    if matches:
        tested_requirement = matches[0]
    else:
        tested_requirement = TestedRequirement(id=short_req_id, scenarios=[])
        tested_package.requirements.append(tested_requirement)

    return tested_requirement


class ScenarioInfo(ImplicitDict):
    """Limited subset of a full TestScenarioReport that still contains enough information to produce a TestedScenario."""

    name: str
    scenario_type: TestScenarioTypeName
    documentation_url: str


def _same_tested_scenario_types(s1: TestedScenario, s2: TestedScenario) -> bool:
    if s1.type.startswith("scenarios.") and s2.type.startswith("scenarios."):
        return are_scenario_types_equal(s1.type, s2.type)
    else:
        return s1.type == s2.type


def _tested_scenario_for(
    default_scenario: TestedScenario, tested_requirement: TestedRequirement
) -> TestedScenario:
    """Retrieves the TestedScenario for the specified scenario within the specified requirement, creating an empty one if necessary.

    Args:
        * default_scenario: The TestedScenario information to use if no pre-existing TestedScenario is found.
        * tested_requirement: The requirement breakdown level for which the scenario is being found.
    """
    matches = [
        s
        for s in tested_requirement.scenarios
        if _same_tested_scenario_types(s, default_scenario)
    ]
    if matches:
        tested_scenario = matches[0]
    else:
        tested_scenario = TestedScenario(
            type=default_scenario.type,
            name=default_scenario.name,
            url=default_scenario.url,
            cases=[],
        )
        tested_requirement.scenarios.append(tested_scenario)

    return tested_scenario


def _add_check_to_breakdown_for_req(
    req_id: RequirementID,
    scenario_report: TestScenarioReport,
    case: TestCaseReport | None,
    step: TestStepReport,
    check: PassedCheck | FailedCheck,
    breakdown: TestedBreakdown,
    acceptable_findings: list[FullyQualifiedCheck],
):
    tested_requirement = _tested_requirement_for(req_id, breakdown)
    tested_scenario = _tested_scenario_for(
        TestedScenario.from_scenario_report(scenario_report), tested_requirement
    )

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
        tested_step = TestedStep(name=step.name, url=step.documentation_url, checks=[])
        tested_case.steps.append(tested_step)

    matches = [c for c in tested_step.checks if c.name == check.name]
    if matches:
        tested_check = matches[0]
    else:
        current_check = FullyQualifiedCheck(
            scenario_type=scenario_report.scenario_type,
            test_case_name=case_name,
            test_step_name=step.name,
            check_name=check.name,
        )
        tested_check = TestedCheck(
            name=check.name,
            url="",
            has_todo=False,
            is_finding_acceptable=fully_qualified_check_in_collection(
                current_check, acceptable_findings
            ),
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
    action: TestSuiteActionDeclaration | PotentialGeneratedAction,
    acceptable_findings: list[FullyQualifiedCheck],
    req_set: set[RequirementID] | None,
) -> None:
    action_type = action.get_action_type()
    if action_type == ActionType.TestScenario:
        _populate_breakdown_with_scenario(
            breakdown, action.test_scenario.scenario_type, acceptable_findings, req_set
        )
    elif action_type == ActionType.TestSuite:
        if "suite_type" in action.test_suite and action.test_suite.suite_type:
            suite_def: TestSuiteDefinition = ImplicitDict.parse(
                load_dict_with_references(action.test_suite.suite_type),
                TestSuiteDefinition,
            )
            for a in suite_def.actions:
                _populate_breakdown_with_action_declaration(
                    breakdown, a, acceptable_findings, req_set
                )
        elif (
            "suite_definition" in action.test_suite
            and action.test_suite.suite_definition
        ):
            for a in action.test_suite.suite_definition.actions:
                _populate_breakdown_with_action_declaration(
                    breakdown, a, acceptable_findings, req_set
                )
        else:
            raise ValueError("Test suite action missing suite type or definition")
    elif action_type == ActionType.ActionGenerator:
        potential_actions = list_potential_actions_for_action_generator_definition(
            action.action_generator
        )
        for a in potential_actions:
            _populate_breakdown_with_action_declaration(
                breakdown, a, acceptable_findings, req_set
            )
    else:
        raise NotImplementedError(f"Unsupported test suite action type: {action_type}")


def _populate_breakdown_with_scenario(
    breakdown: TestedBreakdown,
    scenario_type_name: TestScenarioTypeName,
    acceptable_findings: list[FullyQualifiedCheck],
    req_set: set[RequirementID] | None,
) -> None:
    scenario_type = get_scenario_type_by_name(scenario_type_name)
    scenario_doc = get_documentation(scenario_type)
    for case in scenario_doc.cases:
        for step in case.steps:
            for check in step.checks:
                for req_id in check.applicable_requirements:
                    if req_set is not None and req_id not in req_set:
                        continue
                    tested_requirement = _tested_requirement_for(req_id, breakdown)
                    tested_scenario = _tested_scenario_for(
                        TestedScenario(
                            type=scenario_type_name,
                            name=scenario_doc.name,
                            url=scenario_doc.url,
                            cases=[],
                        ),
                        tested_requirement,
                    )

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
                        current_check = FullyQualifiedCheck(
                            scenario_type=scenario_type_name,
                            test_case_name=case.name,
                            test_step_name=step.name,
                            check_name=check.name,
                        )
                        tested_check = TestedCheck(
                            name=check.name,
                            url=check.url,
                            has_todo=check.has_todo,
                            is_finding_acceptable=fully_qualified_check_in_collection(
                                current_check, acceptable_findings
                            ),
                        )
                        tested_step.checks.append(tested_check)
                    if not tested_check.url:
                        tested_check.url = check.url
