from typing import Dict, Callable, TypeVar, Type

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
from monitoring.uss_qualifier.reports.report import TestSuiteReport
from monitoring.uss_qualifier.requirements.definitions import RequirementID
from monitoring.uss_qualifier.requirements.documentation import (
    resolve_requirements_collection,
)

SpecificConditionType = TypeVar("SpecificConditionType", bound=SpecificCondition)
_capability_condition_evaluators: Dict[
    Type, Callable[[SpecificConditionType, ParticipantID, TestSuiteReport], bool]
] = {}


def capability_condition_evaluator(condition_type: Type):
    """Decorator to label a function that evaluates a specific condition for verifying a capability.

    Args:
        condition_type: A Type that inherits from capability_definitions.SpecificCondition.
    """

    def register_evaluator(func):
        _capability_condition_evaluators[condition_type] = func
        return func

    return register_evaluator


def condition_satisfied_for_test_suite(
    grant_condition: CapabilityVerificationCondition,
    participant_id: ParticipantID,
    report: TestSuiteReport,
) -> bool:
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
) -> bool:
    for subcondition in condition.conditions:
        if not condition_satisfied_for_test_suite(subcondition, participant_id, report):
            return False
    return True


@capability_condition_evaluator(AnyCondition)
def evaluate_any_condition_condition(
    condition: AnyCondition, participant_id: ParticipantID, report: TestSuiteReport
) -> bool:
    for subcondition in condition.conditions:
        if condition_satisfied_for_test_suite(subcondition, participant_id, report):
            return True
    return False


@capability_condition_evaluator(NoFailedChecksCondition)
def evaluate_no_failed_checks_condition(
    condition: NoFailedChecksCondition,
    participant_id: ParticipantID,
    report: TestSuiteReport,
) -> bool:
    for _ in report.query_failed_checks(participant_id):
        return False
    return True


@capability_condition_evaluator(RequirementsCheckedCondition)
def evaluate_requirements_checked_conditions(
    condition: RequirementsCheckedCondition,
    participant_id: ParticipantID,
    report: TestSuiteReport,
) -> bool:
    req_checked: Dict[RequirementID, bool] = {
        req_id: False for req_id in resolve_requirements_collection(condition.checked)
    }
    for passed_check in report.query_passed_checks(participant_id):
        for req_id in passed_check.requirements:
            if req_id in req_checked:
                req_checked[req_id] = True
    outcomes = req_checked.values()
    return outcomes and all(outcomes)


@capability_condition_evaluator(CapabilityVerifiedCondition)
def evaluate_capability_verified_condition(
    condition: CapabilityVerifiedCondition,
    participant_id: ParticipantID,
    report: TestSuiteReport,
) -> bool:
    path = condition.capability_location if "capability_location" in condition else "$"
    matching_reports = bc_jsonpath_ng.ext.parse(path).find(report)
    result = False
    for matching_report in matching_reports:
        if isinstance(matching_report.value, TestSuiteReport):
            capabilities = matching_report.value.capabilities_verified.get(
                participant_id, set()
            )
            if condition.capability_id in capabilities:
                result = True
            else:
                return False
    return result
