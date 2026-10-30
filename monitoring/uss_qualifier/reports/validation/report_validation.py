import json
from collections.abc import Iterator
from dataclasses import dataclass

import yaml
from loguru import logger

from monitoring.monitorlib.dicts import JSONAddress
from monitoring.monitorlib.inspection import fullname
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import FullyQualifiedCheck
from monitoring.uss_qualifier.reports.report import (
    ActionGeneratorReport,
    FailedCheck,
    SkippedActionReport,
    TestRunReport,
    TestScenarioReport,
    TestStepReport,
    TestSuiteActionReport,
    TestSuiteReport,
)
from monitoring.uss_qualifier.reports.validation.definitions import (
    EachElementCondition,
    ElementGroupCondition,
    NumericComparison,
    PassCondition,
    SeverityComparison,
    ValidationConfiguration,
    ValidationCriterion,
    ValidationCriterionApplicability,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    fully_qualified_check_in_collection,
)

# ===== Shared logic =====


@dataclass
class TestReportElement:
    element: FailedCheck | SkippedActionReport | TestScenarioReport
    location: JSONAddress
    is_acceptable: bool = False


def _compare_number(value: float, comparison: NumericComparison) -> bool:
    if comparison.equal_to is not None:
        return value == comparison.equal_to
    elif comparison.at_least is not None:
        return value >= comparison.at_least
    elif comparison.more_than is not None:
        return value > comparison.more_than
    elif comparison.no_more_than is not None:
        return value <= comparison.no_more_than
    elif comparison.less_than is not None:
        return value < comparison.less_than
    else:
        raise ValueError(
            "Invalid NumericComparison; must specify exactly one of the comparison options"
        )


def _compare_severity(severity: Severity, comparison: SeverityComparison) -> bool:
    if comparison.equal_to:
        return severity == comparison.equal_to
    elif comparison.at_least:
        return severity >= comparison.at_least
    elif comparison.higher_than:
        return severity > comparison.higher_than
    elif comparison.no_higher_than:
        return severity <= comparison.no_higher_than
    elif comparison.lower_than:
        return severity < comparison.lower_than
    else:
        raise ValueError(
            "Invalid SeverityComparison; must specify exactly one of the comparison options"
        )


# ===== Enumeration of applicable elements =====


def _is_applicable(
    element: TestReportElement, applicability: ValidationCriterionApplicability
) -> bool:
    if applicability.test_scenarios is not None:
        if not isinstance(element.element, TestScenarioReport):
            return False
        return True

    elif applicability.failed_checks is not None:
        if not isinstance(element.element, FailedCheck):
            return False
        if applicability.failed_checks.has_severity is not None:
            if not _compare_severity(
                element.element.severity, applicability.failed_checks.has_severity
            ):
                return False
        if applicability.failed_checks.is_acceptable is not None:
            if element.is_acceptable != applicability.failed_checks.is_acceptable:
                return False
        return True

    elif applicability.skipped_actions is not None:
        if not isinstance(element.element, SkippedActionReport):
            return False
        return True

    elif applicability.address_is is not None:
        return applicability.address_is == element.location

    elif applicability.does_not_satisfy is not None:
        return not _is_applicable(element, applicability.does_not_satisfy)

    elif applicability.satisfies_all is not None:
        return all(_is_applicable(element, a) for a in applicability.satisfies_all)

    elif applicability.satisfies_any is not None:
        return any(_is_applicable(element, a) for a in applicability.satisfies_any)

    else:
        raise ValueError(
            "Invalid ValidationCriterionApplicability; must specify exactly one of the applicability criteria"
        )


def _get_applicable_elements_from_test_scenario(
    applicability: ValidationCriterionApplicability,
    report: TestScenarioReport,
    location: JSONAddress,
    acceptable_findings: list[FullyQualifiedCheck],
) -> Iterator[TestReportElement]:
    element = TestReportElement(element=report, location=location)
    if _is_applicable(element, applicability):
        yield element
    steps: list[tuple[str, TestStepReport, str]] = [
        (case.name, step, f"cases[{c}].steps[{s}]")
        for c, case in enumerate(report.cases)
        for s, step in enumerate(case.steps)
    ]
    if report.cleanup:
        steps.append(("Cleanup", report.cleanup, "cleanup"))
    for case_name, step, step_location in steps:
        for i, fc in enumerate(step.failed_checks):
            check = FullyQualifiedCheck(
                scenario_type=report.scenario_type,
                test_case_name=case_name,
                test_step_name=step.name,
                check_name=fc.name,
            )
            element = TestReportElement(
                element=fc,
                location=JSONAddress(f"{location}.{step_location}.failed_checks[{i}]"),
                is_acceptable=fully_qualified_check_in_collection(
                    check, acceptable_findings
                ),
            )
            if _is_applicable(element, applicability):
                yield element


def _get_applicable_elements_from_test_suite(
    applicability: ValidationCriterionApplicability,
    report: TestSuiteReport,
    location: JSONAddress,
    acceptable_findings: list[FullyQualifiedCheck],
) -> Iterator[TestReportElement]:
    for a, action in enumerate(report.actions):
        yield from _get_applicable_elements_from_action(
            applicability,
            action,
            JSONAddress(location + f".actions[{a}]"),
            acceptable_findings,
        )


def _get_applicable_elements_from_action_generator(
    applicability: ValidationCriterionApplicability,
    report: ActionGeneratorReport,
    location: JSONAddress,
    acceptable_findings: list[FullyQualifiedCheck],
) -> Iterator[TestReportElement]:
    for a, action in enumerate(report.actions):
        yield from _get_applicable_elements_from_action(
            applicability,
            action,
            JSONAddress(location + f".actions[{a}]"),
            acceptable_findings,
        )


def _get_applicable_elements_from_skipped_action(
    applicability: ValidationCriterionApplicability,
    report: SkippedActionReport,
    location: JSONAddress,
) -> Iterator[TestReportElement]:
    element = TestReportElement(element=report, location=location)
    if _is_applicable(element, applicability):
        yield element


def _get_applicable_elements_from_action(
    applicability: ValidationCriterionApplicability,
    report: TestSuiteActionReport,
    location: JSONAddress,
    acceptable_findings: list[FullyQualifiedCheck],
) -> Iterator[TestReportElement]:
    if report.test_scenario:
        return _get_applicable_elements_from_test_scenario(
            applicability,
            report.test_scenario,
            JSONAddress(location + ".test_scenario"),
            acceptable_findings,
        )
    elif report.test_suite:
        return _get_applicable_elements_from_test_suite(
            applicability,
            report.test_suite,
            JSONAddress(location + ".test_suite"),
            acceptable_findings,
        )
    elif report.action_generator:
        return _get_applicable_elements_from_action_generator(
            applicability,
            report.action_generator,
            JSONAddress(location + ".action_generator"),
            acceptable_findings,
        )
    elif report.skipped_action:
        return _get_applicable_elements_from_skipped_action(
            applicability,
            report.skipped_action,
            JSONAddress(location + ".skipped_action"),
        )
    else:
        raise report.invalid_type_error


# ===== Evaluation of conditions =====


def _evaluate_element_condition(
    condition: EachElementCondition, element: TestReportElement
) -> bool:
    if condition.has_severity is not None:
        if isinstance(element.element, FailedCheck):
            return _compare_severity(element.element.severity, condition.has_severity)
        else:
            logger.warning(
                f"has_severity condition applied to non-FailedCheck element type {fullname(type(element.element))}"
            )
            return False

    elif condition.has_execution_error is not None:
        if isinstance(element.element, TestScenarioReport):
            has_error = element.element.execution_error is not None
            return condition.has_execution_error == has_error
        else:
            return not condition.has_execution_error

    else:
        raise ValueError(
            "Invalid EachElementCondition; must specify exactly one of the options"
        )


def _evaluate_elements_condition(
    condition: ElementGroupCondition, elements: list[TestReportElement]
) -> bool:
    if condition.count is not None:
        return _compare_number(len(elements), condition.count)

    else:
        raise ValueError(
            "Invalid ElementGroupCondition; must specify exactly one of the options"
        )


def _evaluate_condition(
    condition: PassCondition, elements: list[TestReportElement]
) -> bool:
    if condition.each_element is not None:
        for element in elements:
            if not _evaluate_element_condition(condition.each_element, element):
                return False
        return True

    elif condition.elements is not None:
        return _evaluate_elements_condition(condition.elements, elements)

    elif condition.does_not_pass is not None:
        return not _evaluate_condition(condition.does_not_pass, elements)

    elif condition.all_of is not None:
        return all(_evaluate_condition(c, elements) for c in condition.all_of)

    elif condition.any_of is not None:
        return any(_evaluate_condition(c, elements) for c in condition.any_of)

    else:
        raise ValueError(
            "Invalid PassCondition; must specify exactly one of the options"
        )


# ===== Validation =====


def _criterion_validated(criterion: ValidationCriterion, report: TestRunReport) -> bool:
    artifacts = report.configuration.v1.artifacts if report.configuration.v1 else None
    acceptable_findings = list(artifacts.acceptable_findings) if artifacts else []
    elements = list(
        _get_applicable_elements_from_action(
            criterion.applicability, report.report, "$.report", acceptable_findings
        )
    )
    return _evaluate_condition(criterion.pass_condition, elements)


def validate_report(report: TestRunReport, validation: ValidationConfiguration) -> bool:
    """Validate that the provided report meets all the specified validation criteria.

    Validation failures are logged as errors.

    Args:
        report: Report to validate.
        validation: Validation criteria.

    Returns: True if the report satisfies all criteria, False otherwise.
    """
    success = True
    for c, criterion in enumerate(validation.criteria):
        if not _criterion_validated(criterion, report):
            success = False
            logger.error(
                f"Validation criterion {c} failed to validate.  Criterion definition:\n"
                + yaml.dump(json.loads(json.dumps(criterion)))
            )
    return success
