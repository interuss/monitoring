from loguru import logger

from monitoring.monitorlib.dicts import JSONAddress
from monitoring.uss_qualifier.reports.report import TestRunReport, TestSuiteActionReport
from monitoring.uss_qualifier.reports.validation.definitions import (
    ValidationConfiguration,
)


def _validate_action_full_success(
    report: TestSuiteActionReport, context: JSONAddress
) -> bool:
    test_suite, test_scenario, action_generator = report.get_applicable_report()
    if test_scenario:
        success = report.test_scenario.successful
        if not success:
            logger.error(
                f"Full success not achieved because {context}.test_scenario.successful was False"
            )
    elif test_suite:
        if report.test_suite.successful:
            success = True
        else:
            success = False
            logger.error(
                f"Full success not achieved because {context}.test_suite.successful was False"
            )
        for i, a in enumerate(report.test_suite.actions):
            success = success and _validate_action_full_success(
                a, JSONAddress(context + f".test_suite.actions[{i}]")
            )
    elif action_generator:
        if report.action_generator.successful:
            success = True
        else:
            success = False
            logger.error(
                f"Full success not achieved because {context}.action_generator.successful was False"
            )
        for i, a in enumerate(report.action_generator.actions):
            success = success and _validate_action_full_success(
                a, JSONAddress(context + f".action_generator.actions[{i}]")
            )
    else:
        success = True
    return success


def _validate_full_success(report: TestRunReport) -> bool:
    return _validate_action_full_success(report.report, JSONAddress("$"))


def _validate_action_no_skipped_actions(
    report: TestSuiteActionReport, context: JSONAddress
) -> bool:
    test_suite, test_scenario, action_generator = report.get_applicable_report()
    if test_scenario:
        success = True
    elif test_suite:
        success = True
        for i, a in enumerate(report.test_suite.actions):
            success = success and _validate_action_no_skipped_actions(
                a, JSONAddress(context + f".test_suite.actions[{i}]")
            )
    elif action_generator:
        success = True
        for i, a in enumerate(report.action_generator.actions):
            success = success and _validate_action_no_skipped_actions(
                a, JSONAddress(context + f".action_generator.actions[{i}]")
            )
    else:
        logger.error(
            f"No skipped actions not achieved because {context} was a skipped action: {report.skipped_action.reason}"
        )
        success = False
    return success


def _validate_no_skipped_actions(report: TestRunReport) -> bool:
    return _validate_action_no_skipped_actions(report.report, JSONAddress("$"))


def validate_report(report: TestRunReport, validation: ValidationConfiguration) -> bool:
    """Validate that the provided report meets all the specified validation criteria.

    Validation failures are logged as errors.

    Args:
        report: Report to validate.
        validation: Validation criteria.

    Returns: True if the report satisfies all criteria, False otherwise.
    """
    success = True
    for criterion in validation.criteria:
        if criterion.full_success is not None:
            success = success and _validate_full_success(report)
        if criterion.no_skipped_actions is not None:
            success = success and _validate_no_skipped_actions(report)
    return success
