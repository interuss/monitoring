from typing import Dict, Callable, TypeVar, List, Any, Optional

import bc_jsonpath_ng.ext

from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.reports.capability_definitions import (
    AllConditions,
    SpecificCondition,
    AnyCondition,
    NoFailedChecksCondition,
    RequirementsCheckedCondition,
    CapabilityVerifiedCondition,
    CapabilityVerificationCondition,
)
from monitoring.uss_qualifier.reports.report import (
    TestSuiteReport,
    ParticipantCapabilityConditionEvaluationReport,
    AllConditionsEvaluationReport,
    AnyConditionEvaluationReport,
    NoFailedChecksConditionEvaluationReport,
    CheckedRequirement,
    RequirementsCheckedConditionEvaluationReport,
    SpuriousReportMatch,
    CheckedCapability,
    CapabilityVerifiedConditionEvaluationReport,
)
from monitoring.uss_qualifier.requirements.definitions import RequirementID
from monitoring.uss_qualifier.requirements.documentation import (
    resolve_requirements_collection,
)

SpecificConditionType = TypeVar("SpecificConditionType", bound=SpecificCondition)
ConditionEvaluator = Callable[
    [SpecificConditionType, ParticipantID, TestSuiteReport],
    ParticipantCapabilityConditionEvaluationReport,
]
_capability_condition_evaluators: Dict[SpecificConditionType, ConditionEvaluator] = {}


def capability_condition_evaluator(condition_type: SpecificConditionType):
    """Decorator to label a function that evaluates a specific condition for verifying a capability.

    Args:
        condition_type: A Type that inherits from capability_definitions.SpecificCondition.
    """

    def register_evaluator(func: ConditionEvaluator) -> ConditionEvaluator:
        _capability_condition_evaluators[condition_type] = func
        return func

    return register_evaluator


def evaluate_condition_for_test_suite(
    grant_condition: CapabilityVerificationCondition,
    participant_id: ParticipantID,
    report: TestSuiteReport,
) -> ParticipantCapabilityConditionEvaluationReport:
    """Determine if a condition for verifying a capability is satisfied based on a Test Suite report.

    Args:
        grant_condition: Capability-verifying condition to check.
        participant_id: Participant for which the capability would be verified.
        report: Test Suite report upon which the capability (and verification condition) are based.

    Returns: True if the condition was satisfied, False if not.
    """
    populated_fields = [
        field_name
        for field_name in grant_condition
        if grant_condition[field_name] is not None
    ]
    if not populated_fields:
        raise ValueError(
            "No specific condition specified for grant_condition in CapabilityVerificationCondition"
        )
    if len(populated_fields) > 1:
        raise ValueError(
            "Multiple conditions specified for grant_condition in CapabilityVerificationCondition: "
            + ", ".join(populated_fields)
        )
    specific_condition = grant_condition[populated_fields[0]]
    condition_evaluator = _capability_condition_evaluators.get(
        type(specific_condition), None
    )
    if condition_evaluator is None:
        raise RuntimeError(
            f"Could not find evaluator for condition type {type(specific_condition).__name__}"
        )
    return condition_evaluator(specific_condition, participant_id, report)


@capability_condition_evaluator(AllConditions)
def evaluate_all_conditions_condition(
    condition: AllConditions, participant_id: ParticipantID, report: TestSuiteReport
) -> ParticipantCapabilityConditionEvaluationReport:
    satisfied_conditions: List[ParticipantCapabilityConditionEvaluationReport] = []
    unsatisfied_conditions: List[ParticipantCapabilityConditionEvaluationReport] = []
    for subcondition in condition.conditions:
        subreport = evaluate_condition_for_test_suite(
            subcondition, participant_id, report
        )
        if subreport.condition_satisfied:
            satisfied_conditions.append(subreport)
        else:
            unsatisfied_conditions.append(subreport)
    return ParticipantCapabilityConditionEvaluationReport(
        condition_satisfied=len(satisfied_conditions) > 0
        and len(unsatisfied_conditions) == 0,
        all_conditions=AllConditionsEvaluationReport(
            satisfied_conditions=satisfied_conditions,
            unsatisfied_conditions=unsatisfied_conditions,
        ),
    )


@capability_condition_evaluator(AnyCondition)
def evaluate_any_condition_condition(
    condition: AnyCondition, participant_id: ParticipantID, report: TestSuiteReport
) -> ParticipantCapabilityConditionEvaluationReport:
    satisfied_options: List[ParticipantCapabilityConditionEvaluationReport] = []
    unsatisfied_options: List[ParticipantCapabilityConditionEvaluationReport] = []
    for subcondition in condition.conditions:
        subreport = evaluate_condition_for_test_suite(
            subcondition, participant_id, report
        )
        if subreport.condition_satisfied:
            satisfied_options.append(subreport)
        else:
            unsatisfied_options.append(subreport)
    return ParticipantCapabilityConditionEvaluationReport(
        condition_satisfied=len(satisfied_options) > 0,
        all_conditions=AnyConditionEvaluationReport(
            satisfied_options=satisfied_options, unsatisfied_options=unsatisfied_options
        ),
    )


@capability_condition_evaluator(NoFailedChecksCondition)
def evaluate_no_failed_checks_condition(
    condition: NoFailedChecksCondition,
    participant_id: ParticipantID,
    report: TestSuiteReport,
) -> ParticipantCapabilityConditionEvaluationReport:
    failed_check_paths = [
        "$." + path for path, _ in report.query_failed_checks(participant_id)
    ]
    return ParticipantCapabilityConditionEvaluationReport(
        condition_satisfied=len(failed_check_paths) == 0,
        no_failed_checks=NoFailedChecksConditionEvaluationReport(
            failed_checks=failed_check_paths
        ),
    )


@capability_condition_evaluator(RequirementsCheckedCondition)
def evaluate_requirements_checked_conditions(
    condition: RequirementsCheckedCondition,
    participant_id: ParticipantID,
    report: TestSuiteReport,
) -> ParticipantCapabilityConditionEvaluationReport:
    req_checks: Dict[RequirementID, CheckedRequirement] = {
        req_id: CheckedRequirement(
            requirement_id=req_id, passed_checks=[], failed_checks=[]
        )
        for req_id in resolve_requirements_collection(condition.checked)
    }
    for path, passed_check in report.query_passed_checks(participant_id):
        for req_id in passed_check.requirements:
            if req_id in req_checks:
                req_checks[req_id].passed_checks.append("$." + path)
    for path, failed_check in report.query_failed_checks(participant_id):
        for req_id in failed_check.requirements:
            if req_id in req_checks:
                req_checks[req_id].failed_checks.append("$." + path)
    passed = [
        cr for cr in req_checks.values() if cr.passed_checks and not cr.failed_checks
    ]
    failed = [cr for cr in req_checks.values() if cr.failed_checks]
    untested = [
        cr.requirement_id
        for cr in req_checks.values()
        if not cr.passed_checks and not cr.failed_checks
    ]
    return ParticipantCapabilityConditionEvaluationReport(
        condition_satisfied=all(cr.passed_checks for cr in req_checks.values())
        and not any(cr.failed_checks for cr in req_checks.values()),
        requirements_checked=RequirementsCheckedConditionEvaluationReport(
            passed_requirements=passed,
            failed_requirements=failed,
            untested_requirements=untested,
        ),
    )


def _jsonpath_of(descendant: Any, ancestor: Any) -> Optional[str]:
    """Construct a relative JSONPath to descendant from ancestor by exhaustive reference equality search.

    One would think this functionality would be part of the jsonpath_ng package when producing matches, but one would
    apparently be wrong.  This approach is monstrously inefficient, but easy to write and easy to understand.
    """
    if ancestor is descendant:
        return ""
    elif isinstance(ancestor, dict):
        for k, v in ancestor.items():
            subpath = _jsonpath_of(descendant, v)
            if subpath is not None:
                return f".{k}{subpath}"
        return None
    elif isinstance(ancestor, list):
        for i, v in enumerate(ancestor):
            subpath = _jsonpath_of(descendant, v)
            if subpath is not None:
                return f"[{i}]{subpath}"
    else:
        return None


@capability_condition_evaluator(CapabilityVerifiedCondition)
def evaluate_capability_verified_condition(
    condition: CapabilityVerifiedCondition,
    participant_id: ParticipantID,
    report: TestSuiteReport,
) -> ParticipantCapabilityConditionEvaluationReport:
    path = condition.capability_location if "capability_location" in condition else "$"
    matching_reports = bc_jsonpath_ng.ext.parse(path).find(report)
    checked_capabilities = []
    spurious_matches = []
    for matching_report in matching_reports:
        if isinstance(matching_report.value, TestSuiteReport):
            for i, capability_eval in enumerate(
                matching_report.value.capability_evaluations
            ):
                if capability_eval.participant_id != participant_id:
                    continue
                if capability_eval.capability_id not in condition.capability_ids:
                    continue
                report_path = "$" + _jsonpath_of(matching_report.value, report)
                checked_capabilities.append(
                    CheckedCapability(
                        report_location=report_path,
                        capability_id=capability_eval.capability_id,
                        capability_location=f"{report_path}.capability_evaluations[{i}]",
                        capability_verified=capability_eval.verified,
                    )
                )
        else:
            spurious_matches.append(
                SpuriousReportMatch(
                    location="$" + _jsonpath_of(matching_report.value, report),
                    type=type(matching_report.value).__name__,
                )
            )
    found_capabilities = {cc.capability_id for cc in checked_capabilities}
    missing_capabilities = [
        c for c in condition.capability_ids if c not in found_capabilities
    ]
    return ParticipantCapabilityConditionEvaluationReport(
        condition_satisfied=all(cc.capability_verified for cc in checked_capabilities)
        and len(missing_capabilities) == 0,
        capability_verified=CapabilityVerifiedConditionEvaluationReport(
            checked_capabilities=checked_capabilities,
            missing_capabilities=missing_capabilities,
            spurious_matches=spurious_matches,
        ),
    )
