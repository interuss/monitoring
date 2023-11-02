import json
from dataclasses import dataclass
from typing import Iterator, Union, List

from loguru import logger
import yaml

from monitoring.monitorlib.dicts import JSONAddress
from monitoring.monitorlib.inspection import fullname
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.reports.report import (
    TestRunReport,
    TestSuiteActionReport,
    FailedCheck,
    TestSuiteReport,
    ActionGeneratorReport,
    SkippedActionReport,
    TestScenarioReport,
)
from monitoring.uss_qualifier.reports.validation.definitions import (
    ValidationConfiguration,
    ValidationCriterion,
    ValidationCriterionApplicability,
    SeverityComparison,
    PassCondition,
    EachElementCondition,
    ElementGroupCondition,
    NumericComparison,
)


# ===== Shared logic =====


@dataclass
class TestReportElement(object):
    element: Union[FailedCheck, SkippedActionReport, TestScenarioReport]
    location: JSONAddress


def _compare_number(value: float, comparison: NumericComparison) -> bool:
    if "equal_to" in comparison and comparison.equal_to is not None:
        return value == comparison.equal_to
    elif "at_least" in comparison and comparison.at_least is not None:
        return value >= comparison.at_least
    elif "more_than" in comparison and comparison.more_than is not None:
        return value > comparison.more_than
    elif "no_more_than" in comparison and comparison.no_more_than is not None:
        return value <= comparison.no_more_than
    elif "less_than" in comparison and comparison.less_than is not None:
        return value < comparison.less_than
    else:
        raise ValueError(
            "Invalid NumericComparison; must specify exactly one of the comparison options"
        )


def _compare_severity(severity: Severity, comparison: SeverityComparison) -> bool:
    if "equal_to" in comparison and comparison.equal_to:
        return severity == comparison.equal_to
    elif "at_least" in comparison and comparison.at_least:
        return severity >= comparison.at_least
    elif "higher_than" in comparison and comparison.higher_than:
        return severity > comparison.higher_than
    elif "no_higher_than" in comparison and comparison.no_higher_than:
        return severity <= comparison.no_higher_than
    elif "lower_than" in comparison and comparison.lower_than:
        return severity < comparison.lower_than
    else:
        raise ValueError(
            "Invalid SeverityComparison; must specify exactly one of the comparison options"
        )


# ===== Enumeration of applicable elements =====


def _is_applicable(
    element: TestReportElement, applicability: ValidationCriterionApplicability
) -> bool:
    if "test_scenarios" in applicability and applicability.test_scenarios is not None:
        if not isinstance(element.element, TestScenarioReport):
            return False
        return True

    elif "failed_checks" in applicability and applicability.failed_checks is not None:
        if not isinstance(element.element, FailedCheck):
            return False
        if (
            "has_severity" in applicability.failed_checks
            and applicability.failed_checks.has_severity is not None
        ):
            if not _compare_severity(
                element.element.severity, applicability.failed_checks.has_severity
            ):
                return False
        return True

    elif (
        "skipped_actions" in applicability and applicability.skipped_actions is not None
    ):
        if not isinstance(element.element, SkippedActionReport):
            return False
        return True

    elif "address_is" in applicability and applicability.address_is is not None:
        return applicability.address_is == element.location

    elif (
        "does_not_satisfy" in applicability
        and applicability.does_not_satisfy is not None
    ):
        return not _is_applicable(element, applicability.does_not_satisfy)

    elif "satisfies_all" in applicability and applicability.satisfies_all is not None:
        return all(_is_applicable(element, a) for a in applicability.satisfies_all)

    elif "satisfies_any" in applicability and applicability.satisfies_any is not None:
        return any(_is_applicable(element, a) for a in applicability.satisfies_any)

    else:
        raise ValueError(
            "Invalid ValidationCriterionApplicability; must specify exactly one of the applicability criteria"
        )


def _get_applicable_elements_from_test_scenario(
    applicability: ValidationCriterionApplicability,
    report: TestScenarioReport,
    location: JSONAddress,
) -> Iterator[TestReportElement]:
    element = TestReportElement(element=report, location=location)
    if _is_applicable(element, applicability):
        yield element
    for i, (fc_location, fc) in enumerate(report.query_failed_checks()):
        element = TestReportElement(
            element=fc, location=JSONAddress(location + "." + fc_location)
        )
        if _is_applicable(element, applicability):
            yield element


def _get_applicable_elements_from_test_suite(
    applicability: ValidationCriterionApplicability,
    report: TestSuiteReport,
    location: JSONAddress,
) -> Iterator[TestReportElement]:
    for a, action in enumerate(report.actions):
        for e in _get_applicable_elements_from_action(
            applicability, action, JSONAddress(location + f".actions[{a}]")
        ):
            yield e


def _get_applicable_elements_from_action_generator(
    applicability: ValidationCriterionApplicability,
    report: ActionGeneratorReport,
    location: JSONAddress,
) -> Iterator[TestReportElement]:
    for a, action in enumerate(report.actions):
        for e in _get_applicable_elements_from_action(
            applicability, action, JSONAddress(location + f".actions[{a}]")
        ):
            yield e


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
) -> Iterator[TestReportElement]:
    test_suite, test_scenario, action_generator = report.get_applicable_report()
    if test_scenario:
        return _get_applicable_elements_from_test_scenario(
            applicability,
            report.test_scenario,
            JSONAddress(location + ".test_scenario"),
        )
    elif test_suite:
        return _get_applicable_elements_from_test_suite(
            applicability, report.test_suite, JSONAddress(location + ".test_suite")
        )
    elif action_generator:
        return _get_applicable_elements_from_action_generator(
            applicability,
            report.action_generator,
            JSONAddress(location + ".action_generator"),
        )
    else:
        return _get_applicable_elements_from_skipped_action(
            applicability,
            report.skipped_action,
            JSONAddress(location + ".skipped_action"),
        )


# ===== Evaluation of conditions =====


def _evaluate_element_condition(
    condition: EachElementCondition, element: TestReportElement
) -> bool:
    if "has_severity" in condition and condition.has_severity is not None:
        if isinstance(element.element, FailedCheck):
            return _compare_severity(element.element.severity, condition.has_severity)
        else:
            logger.warning(
                f"has_severity condition applied to non-FailedCheck element type {fullname(type(element.element))}"
            )
            return False

    elif (
        "has_execution_error" in condition and condition.has_execution_error is not None
    ):
        if isinstance(element.element, TestScenarioReport):
            has_error = (
                "execution_error" in element.element
                and element.element.execution_error is not None
            )
            return condition.has_execution_error == has_error
        else:
            return not condition.has_execution_error

    else:
        raise ValueError(
            "Invalid EachElementCondition; must specify exactly one of the options"
        )


def _evaluate_elements_condition(
    condition: ElementGroupCondition, elements: List[TestReportElement]
) -> bool:
    if "count" in condition and condition.count is not None:
        return _compare_number(len(elements), condition.count)

    else:
        raise ValueError(
            "Invalid ElementGroupCondition; must specify exactly one of the options"
        )


def _evaluate_condition(
    condition: PassCondition, elements: List[TestReportElement]
) -> bool:
    if "each_element" in condition and condition.each_element is not None:
        for element in elements:
            if not _evaluate_element_condition(condition.each_element, element):
                return False
        return True

    elif "elements" in condition and condition.elements is not None:
        return _evaluate_elements_condition(condition.elements, elements)

    elif "does_not_pass" in condition and condition.does_not_pass is not None:
        return not _evaluate_condition(condition.does_not_pass, elements)

    elif "all_of" in condition and condition.all_of is not None:
        return all(_evaluate_condition(c, elements) for c in condition.all_of)

    elif "any_of" in condition and condition.any_of is not None:
        return any(_evaluate_condition(c, elements) for c in condition.any_of)

    else:
        raise ValueError(
            "Invalid PassCondition; must specify exactly one of the options"
        )


# ===== Validation =====


def _criterion_validated(criterion: ValidationCriterion, report: TestRunReport) -> bool:
    elements = list(
        _get_applicable_elements_from_action(
            criterion.applicability, report.report, "$.report"
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
