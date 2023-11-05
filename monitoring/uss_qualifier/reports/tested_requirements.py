import json
import os
from dataclasses import dataclass
from enum import Enum
from functools import cmp_to_key
from typing import List, Union, Dict, Set, Optional

from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.monitorlib.inspection import import_submodules
from monitoring.monitorlib.versioning import repo_url_of
from monitoring.uss_qualifier import scenarios, suites, action_generators
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_generator_definition,
)
from monitoring.uss_qualifier.configurations.configuration import (
    ParticipantID,
    TestedRequirementsConfiguration,
    TestedRequirementsCollectionIdentifier,
)
from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.reports import jinja_env
from monitoring.uss_qualifier.reports.report import (
    TestRunReport,
    TestSuiteActionReport,
    TestScenarioReport,
    PassedCheck,
    FailedCheck,
)
from monitoring.uss_qualifier.requirements.definitions import RequirementID, PackageID
from monitoring.uss_qualifier.requirements.documentation import (
    resolve_requirements_collection,
)
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioTypeName
from monitoring.uss_qualifier.scenarios.documentation.parsing import get_documentation
from monitoring.uss_qualifier.scenarios.scenario import get_scenario_type_by_name
from monitoring.uss_qualifier.signatures import compute_signature
from monitoring.uss_qualifier.suites.definitions import (
    TestSuiteActionDeclaration,
    ActionType,
    TestSuiteDefinition,
)

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


class RequirementsVerificationReport(ImplicitDict):
    test_run_information: TestRunInformation
    participant_verifications: Dict[ParticipantID, ParticipantVerificationStatus]


def generate_tested_requirements(
    report: TestRunReport, config: TestedRequirementsConfiguration, output_path: str
) -> None:
    req_collections: Dict[
        TestedRequirementsCollectionIdentifier, Set[RequirementID]
    ] = {}
    if "requirement_collections" in config and config.requirement_collections:
        req_collections = {
            k: resolve_requirements_collection(v)
            for k, v in config.requirement_collections.items()
        }

    participant_req_collections: Dict[ParticipantID, Set[RequirementID]] = {}
    if "participant_requirements" in config and config.participant_requirements:
        for k, v in config.participant_requirements.items():
            if v not in req_collections:
                raise ValueError(
                    f"Participant {k}'s requirement collection {v} is not defined in `requirement_collections` of TestedRequirementsConfiguration"
                )
            participant_req_collections[k] = req_collections[v]

    import_submodules(scenarios)
    import_submodules(suites)
    import_submodules(action_generators)

    test_run = compute_test_run_information(report)

    os.makedirs(output_path, exist_ok=True)
    index_file = os.path.join(output_path, "index.html")

    participant_ids = list(report.report.participant_ids())
    participant_ids.sort()
    template = jinja_env.get_template("tested_requirements/test_run_report.html")
    with open(index_file, "w") as f:
        f.write(template.render(participant_ids=participant_ids))

    verification_report = RequirementsVerificationReport(
        test_run_information=test_run, participant_verifications={}
    )
    template = jinja_env.get_template(
        "tested_requirements/participant_tested_requirements.html"
    )
    for participant_id in participant_ids:
        req_set = participant_req_collections.get(participant_id, None)
        participant_breakdown = TestedBreakdown(packages=[])
        _populate_breakdown_with_action_report(
            participant_breakdown, report.report, participant_id, req_set
        )
        _populate_breakdown_with_action_declaration(
            participant_breakdown, report.configuration.action, req_set
        )
        if participant_id in participant_req_collections:
            _populate_breakdown_with_req_set(
                participant_breakdown, participant_req_collections[participant_id]
            )
        _sort_breakdown(participant_breakdown)
        overall_status = _compute_overall_status(participant_breakdown)
        verification_report.participant_verifications[participant_id] = overall_status
        system_version = _find_participant_system_version(report.report, participant_id)
        participant_file = os.path.join(output_path, f"{participant_id}.html")
        other_participants = ", ".join(
            p for p in participant_ids if p != participant_id
        )
        with open(participant_file, "w") as f:
            f.write(
                template.render(
                    participant_id=participant_id,
                    other_participants=other_participants,
                    breakdown=participant_breakdown,
                    test_run=test_run,
                    overall_status=overall_status,
                    system_version=system_version,
                    ParticipantVerificationStatus=ParticipantVerificationStatus,
                )
            )

    status_file = os.path.join(output_path, "status.json")
    with open(status_file, "w") as f:
        json.dump(verification_report, f, indent=2)


def compute_test_run_information(report: TestRunReport) -> TestRunInformation:
    def print_datetime(t: Optional[StringBasedDateTime]) -> Optional[str]:
        if t is None:
            return None
        return t.datetime.strftime("%Y-%m-%d %H:%M:%S %Z")

    return TestRunInformation(
        test_run_id=compute_signature(report),
        start_time=print_datetime(report.report.start_time),
        end_time=print_datetime(report.report.end_time),
        baseline=report.baseline_signature,
        environment=report.environment_signature,
    )


def _compute_overall_status(
    participant_breakdown: TestedBreakdown,
) -> ParticipantVerificationStatus:
    overall_status = ParticipantVerificationStatus.Pass
    for package in participant_breakdown.packages:
        for req in package.requirements:
            if req.classname == FAIL_CLASS:
                return ParticipantVerificationStatus.Fail
            elif req.classname == NOT_TESTED_CLASS:
                overall_status = ParticipantVerificationStatus.Incomplete
            elif req.classname == PASS_CLASS:
                pass
            else:
                return ParticipantVerificationStatus.Unknown
    return overall_status


def _find_participant_system_version(
    report: TestSuiteActionReport, participant_id: ParticipantID
) -> Optional[str]:
    test_suite, test_scenario, action_generator = report.get_applicable_report()
    if test_suite:
        for action in report.test_suite.actions:
            version = _find_participant_system_version(action, participant_id)
            if version is not None:
                return version
    elif action_generator:
        for action in report.action_generator.actions:
            version = _find_participant_system_version(action, participant_id)
            if version is not None:
                return version
    elif test_scenario:
        if report.test_scenario.scenario_type in (
            "scenarios.versioning.get_system_versions.GetSystemVersions",
            "scenarios.versioning.GetSystemVersions",
        ):
            if participant_id in report.test_scenario.notes:
                system_identity, version = report.test_scenario.notes[
                    participant_id
                ].message.split("=")
                return version
    return None


def _split_strings_numbers(s: str) -> List[Union[int, str]]:
    digits = "0123456789"
    current_number = ""
    current_string = ""
    parts = []
    for si in s:
        if si in digits:
            if current_string:
                parts.append(current_string)
                current_string = ""
            current_number += si
        else:
            if current_number:
                parts.append(int(current_number))
                current_number = ""
            current_string += si
    if current_number:
        parts.append(int(current_number))
    elif current_string:
        parts.append(current_string)
    return parts


def _requirement_id_parts(req_id: str) -> List[str]:
    """Split a requirement ID into sortable parts.

    Each ID is split into parts in multiple phases (example: astm.f3411.v22a.NET0260,Table1,1b):
      * Split at periods (splits into package and plain ID)
        * Example: ["astm", "f3411", "v22a", "NET0260,Table1,1b"]
      * Split at commas (splits portions of plain ID by convention)
        * Example: ["astm", "f3411", "v22a", "NET0260", "Table1", "1b"]
      * Split at transitions between words and numbers (so numbers are their own parts and non-numbers are their own parts)
        * Example: ["astm", "f", 3411, "v", 22, "a", "NET", 260, "Table", 1, 1, "b"]

    Args:
        req_id: Requirement ID to split.

    Returns: Constituent parts of req_id.
    """
    old_parts = req_id.split(".")
    parts = []
    for p in old_parts:
        parts.extend(p.split(","))
    old_parts = parts
    parts = []
    for p in old_parts:
        parts.extend(_split_strings_numbers(p))
    return parts


def _compare_requirement_ids(r1: TestedRequirement, r2: TestedRequirement) -> int:
    """Compare requirement IDs for the purpose of sorting.

    The requirement IDs are split into parts and then the parts compared.  If all parts are equal but one ID has more
    parts, the ID with fewer parts is first.  See _requirement_id_parts for how requirement IDs are split.

    Returns:
        * -1 if r1 should be before r2
        * 0 if r1 is equal to r2
        * 1 if r1 should be after r2
    """
    parts1 = _requirement_id_parts(r1.id)
    parts2 = _requirement_id_parts(r2.id)
    i = 0
    while i < min(len(parts1), len(parts2)):
        p1 = parts1[i]
        p2 = parts2[i]
        if p1 == p2:
            i += 1
            continue
        if isinstance(p1, int):
            if isinstance(p2, int):
                return -1 if p1 < p2 else 1
            else:
                return -1
        else:
            if isinstance(p2, int):
                return 1
            else:
                return -1 if p1 < p2 else 1
    if i == len(parts1) and i == len(parts2):
        return 0
    return -1 if len(parts1) < len(parts2) else 1


def _sort_breakdown(breakdown: TestedBreakdown) -> None:
    breakdown.packages.sort(key=lambda p: p.id)
    for package in breakdown.packages:
        package.requirements.sort(key=cmp_to_key(_compare_requirement_ids))
        for requirement in package.requirements:
            requirement.scenarios.sort(key=lambda s: s.name)


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
    participant_id: ParticipantID,
    req_set: Optional[Set[RequirementID]],
) -> None:
    test_suite, test_scenario, action_generator = action.get_applicable_report()
    if test_scenario:
        return _populate_breakdown_with_scenario_report(
            breakdown, action.test_scenario, participant_id, req_set
        )
    elif test_suite:
        for subaction in action.test_suite.actions:
            _populate_breakdown_with_action_report(
                breakdown, subaction, participant_id, req_set
            )
    elif action_generator:
        for subaction in action.action_generator.actions:
            _populate_breakdown_with_action_report(
                breakdown, subaction, participant_id, req_set
            )
    else:
        pass  # Skipped action


def _populate_breakdown_with_scenario_report(
    breakdown: TestedBreakdown,
    scenario_report: TestScenarioReport,
    participant_id: ParticipantID,
    req_set: Optional[Set[RequirementID]],
) -> None:
    scenario_type_name = scenario_report.scenario_type
    for case in scenario_report.cases:
        for step in case.steps:
            for check in step.passed_checks + step.failed_checks:
                if participant_id not in check.participants:
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
                        tested_check = TestedCheck(
                            name=check.name, url="", has_todo=False
                        )  # TODO: Consider populating has_todo with documentation instead
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
