from __future__ import annotations

from implicitdict import ImplicitDict

from monitoring.monitorlib.dicts import JSONAddress
from monitoring.uss_qualifier.common_data_definitions import Severity

# ===== Shared logic =====


class SeverityComparison(ImplicitDict):
    """Exactly one field must be specified."""

    equal_to: Severity | None
    at_least: Severity | None
    higher_than: Severity | None
    no_higher_than: Severity | None
    lower_than: Severity | None


class NumericComparison(ImplicitDict):
    """Exactly one field must be specified."""

    equal_to: float | None
    at_least: float | None
    more_than: float | None
    no_more_than: float | None
    less_than: float | None


# ===== Applicability =====


class TestScenarioApplicability(ImplicitDict):
    """TestScenarioReport test report elements are applicable according to this specification."""

    pass


class FailedCheckApplicability(ImplicitDict):
    """FailedCheck test report elements are applicable according to this specification."""

    has_severity: SeverityComparison | None
    """If specified, only FailedChecks with specified severity are applicable."""


class SkippedCheckApplicability(ImplicitDict):
    """SkippedCheckReport test report elements are applicable according to this specification."""

    pass


class AllCriteriaApplicability(ImplicitDict):
    """All criteria must be met for an element to be applicable."""

    criteria: list[ValidationCriterionApplicability]
    """Criteria that must all be met."""


class AnyCriteriaApplicability(ImplicitDict):
    """Any criterion or criteria must be met for an element to be applicable."""

    criteria: list[ValidationCriterionApplicability]
    """Options for criterion/criteria to meet."""


class ValidationCriterionApplicability(ImplicitDict):
    """A single criterion for determining whether a test report element is applicable.

    Exactly one field must be specified."""

    test_scenarios: TestScenarioApplicability | None
    """Only this kind of TestScenarioReport elements are applicable."""

    failed_checks: FailedCheckApplicability | None
    """Only this kind of FailedCheck elements are applicable."""

    skipped_actions: SkippedCheckApplicability | None
    """Only this kind of SkippedCheckReport elements are applicable."""

    address_is: JSONAddress | None
    """Only the element at this JSONAddress in the test report is applicable."""

    does_not_satisfy: ValidationCriterionApplicability | None
    """Only elements that do not satisfy this criterion are applicable."""

    satisfies_all: AllCriteriaApplicability | None
    """Only elements which satisfy all these criteria are applicable."""

    satisfies_any: AnyCriteriaApplicability | None
    """Elements which satisfy any of these criteria are applicable."""


# ===== Pass conditions =====


class EachElementCondition(ImplicitDict):
    """A single applicable element must meet this condition.  Exactly one field must be specified."""

    has_severity: SeverityComparison | None
    """The element must be a FailedCheck that has this specified kind of severity."""

    has_execution_error: bool | None
    """The element must be a TestScenarioReport that either must have or must not have an execution error."""


class ElementGroupCondition(ImplicitDict):
    """A group of applicable elements must meet this condition.  Exactly one field must be specified."""

    count: NumericComparison | None
    """The number of applicable elements must have this specified kind of count."""


class AllPassConditions(ImplicitDict):
    """All specific conditions must be met."""

    conditions: list[PassCondition]
    """Conditions that all must be met."""


class AnyPassCondition(ImplicitDict):
    """Any specific condition must be met."""

    conditions: list[PassCondition]
    """Options for conditions to meet."""


class PassCondition(ImplicitDict):
    """Condition for passing validation.  Exactly one field must be specified."""

    each_element: EachElementCondition | None
    """Condition applies to each applicable element."""

    elements: ElementGroupCondition | None
    """Condition applies to the group of applicable elements."""

    does_not_pass: PassCondition | None
    """Overall condition is met only if this specified condition is not met."""

    all_of: AllPassConditions | None
    """Overall condition is met only if all of these specified conditions are met."""

    any_of: AnyPassCondition | None
    """Overall condition is met if any of these specified conditions are met."""


# ===== Configuration =====


class ValidationCriterion(ImplicitDict):
    """Wrapper for all the potential types of validation criteria."""

    applicability: ValidationCriterionApplicability
    """Definition of the test report elements to which the `pass_condition` is applicable."""

    pass_condition: PassCondition
    """Condition that must be met by the applicable test report element(s) in order to pass validation."""


class ValidationConfiguration(ImplicitDict):
    """Complete set of validation criteria that a test run report must satisfy."""

    criteria: list[ValidationCriterion]
    """Set of criteria which must all pass in order to pass validation."""
