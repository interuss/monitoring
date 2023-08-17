import os
import shutil
from dataclasses import dataclass
from typing import List, Any, Union, Dict

from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.reports import jinja_env
from monitoring.uss_qualifier.reports.report import (
    TestRunReport,
    TestSuiteActionReport,
    TestScenarioReport,
    ActionGeneratorReport,
    TestSuiteReport,
    PassedCheck,
    FailedCheck,
    ParticipantCapabilityConditionEvaluationReport,
)
from monitoring.uss_qualifier.requirements.definitions import RequirementID


def generate_tested_roles(report: TestRunReport, output_path: str) -> None:
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    participant_ids = report.report.participant_ids()
    for participant_id in participant_ids:
        _generate_suite_action_output(
            report.report, participant_id, os.path.join(output_path, participant_id)
        )
    template = jinja_env.get_template("tested_roles/test_run_report.html")
    index = os.path.join(output_path, "index.html")
    os.makedirs(os.path.dirname(index), exist_ok=True)
    with open(index, "w") as f:
        f.write(template.render(participant_ids=participant_ids))


def _generate_suite_action_output(
    report: TestSuiteActionReport, participant_id: ParticipantID, output_path: str
) -> None:
    test_suite, test_scenario, action_generator = report.get_applicable_report()
    if test_suite:
        _generate_suite_output(report.test_suite, participant_id, output_path)
    elif test_scenario:
        _generate_scenario_output(report.test_scenario, participant_id, output_path)
    elif action_generator:
        _generate_action_generator_output(
            report.action_generator, participant_id, output_path
        )
    else:
        raise ValueError("TestSuiteActionReport did not specify any report")


def _generate_scenario_output(
    report: TestScenarioReport, participant_id: ParticipantID, output_path: str
) -> None:
    pass


def _generate_action_generator_output(
    report: ActionGeneratorReport, participant_id: ParticipantID, output_path: str
) -> None:
    for i, action in enumerate(report.actions):
        _generate_suite_action_output(
            action, participant_id, os.path.join(output_path, f"action{i}")
        )


@dataclass
class PotentiallyCheckedRequirement(object):
    requirement_id: RequirementID
    passed_checks: Dict[str, int]
    failed_checks: List[FailedCheck]

    @property
    def rows(self) -> int:
        if not self.passed_checks and not self.failed_checks:
            return 1
        return len(self.passed_checks) + len(self.failed_checks)


@dataclass
class ChildCapability(object):
    capability_id: str
    verified: bool = False
    missing: bool = False

    @property
    def rows(self) -> int:
        return 1


@dataclass
class CapabilityEvalInfo(object):
    requirements: List[PotentiallyCheckedRequirement]
    capabilities: List[ChildCapability]


@dataclass
class CapabilityEvalReport(object):
    name: str
    verified: bool
    requirements: List[PotentiallyCheckedRequirement]
    capabilities: List[ChildCapability]

    @property
    def rows(self) -> int:
        n = 0
        if self.requirements:
            n += 1
            n += sum(r.rows for r in self.requirements)
        if self.capabilities:
            n += 1
            n += sum(c.rows for c in self.capabilities)
        return n


def _follow_jsonpath(obj: dict, fields: Union[str, List[str]]) -> Any:
    """Follows an explicit JSONPath for an obj (much, much faster than treating path as a search)."""

    if isinstance(fields, str):
        return _follow_jsonpath(obj, fields.split("."))
    if not fields:
        return obj
    if fields[0] == "$" or fields[0] == "":
        return _follow_jsonpath(obj, fields[1:])

    if len(fields) == 1:
        field = fields[0]
        if field[-1] == "]" and "[" in field:
            field, index = field[0:-1].split("[")
            items = _follow_jsonpath(obj, field)
            return items[int(index)]
        else:
            return obj[field]
    else:
        child = _follow_jsonpath(obj, [fields[0]])
        return _follow_jsonpath(child, fields[1:])


def _collect_info_from_conditions(
    report: TestSuiteReport, condition: ParticipantCapabilityConditionEvaluationReport
) -> CapabilityEvalInfo:
    result = CapabilityEvalInfo(requirements=[], capabilities=[])
    if "all_conditions" in condition and condition.all_conditions:
        for subcondition in (
            condition.all_conditions.satisfied_conditions
            + condition.all_conditions.unsatisfied_conditions
        ):
            subresult = _collect_info_from_conditions(report, subcondition)
            result.requirements.extend(subresult.requirements)
            result.capabilities.extend(subresult.capabilities)
    elif "requirements_checked" in condition and condition.requirements_checked:
        for req_ref in (
            condition.requirements_checked.passed_requirements
            + condition.requirements_checked.failed_requirements
        ):
            passed_checks = {}
            failed_checks = []
            for req_path in req_ref.passed_checks:
                pc: PassedCheck = _follow_jsonpath(report, req_path)
                passed_checks[pc.name] = passed_checks.get(pc.name, 0) + 1
            for req_path in req_ref.failed_checks:
                failed_checks.append(_follow_jsonpath(report, req_path))
            req = PotentiallyCheckedRequirement(
                requirement_id=req_ref.requirement_id,
                passed_checks=passed_checks,
                failed_checks=failed_checks,
            )
            result.requirements.append(req)
        for req_id in condition.requirements_checked.untested_requirements:
            result.requirements.append(
                PotentiallyCheckedRequirement(
                    requirement_id=req_id, passed_checks={}, failed_checks=[]
                )
            )
    elif "capability_verified" in condition and condition.capability_verified:
        for c in condition.capability_verified.checked_capabilities:
            result.capabilities.append(
                ChildCapability(
                    capability_id=c.capability_id, verified=c.capability_verified
                )
            )
        for c in condition.capability_verified.missing_capabilities:
            result.capabilities.append(ChildCapability(capability_id=c, missing=True))
    return result


def _generate_suite_output(
    report: TestSuiteReport, participant_id: ParticipantID, output_path: str
) -> None:
    capabilities: List[CapabilityEvalReport] = []
    for capability in report.capability_evaluations:
        if capability.participant_id != participant_id:
            continue
        info = _collect_info_from_conditions(report, capability.condition_evaluation)
        capabilities.append(
            CapabilityEvalReport(
                name=capability.capability_id,
                verified=capability.verified,
                requirements=info.requirements,
                capabilities=info.capabilities,
            )
        )
    template = jinja_env.get_template("tested_roles/capability_evaluation_report.html")
    index = os.path.join(output_path, "index.html")
    os.makedirs(os.path.dirname(index))
    with open(index, "w") as f:
        f.write(
            template.render(
                len=len, test_suite_name=report.name, capabilities=capabilities
            )
        )

    for i, action in enumerate(report.actions):
        _generate_suite_action_output(
            action, participant_id, os.path.join(output_path, f"action{i}")
        )
