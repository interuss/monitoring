from typing import Optional, List

from implicitdict import ImplicitDict


class FullSuccessCriterion(ImplicitDict):
    """Validation criterion that every element of the report must indicate success."""

    pass


class NoSkippedActionsCriterion(ImplicitDict):
    """Validation criterion that no actions in the entire test run may be skipped."""

    pass


class ValidationCriterion(ImplicitDict):
    """Wrapper for all the potential types of validation criteria."""

    full_success: Optional[FullSuccessCriterion] = None
    no_skipped_actions: Optional[NoSkippedActionsCriterion] = None


class ValidationConfiguration(ImplicitDict):
    """Complete set of validation criteria that a test run report must satisfy."""

    criteria: List[ValidationCriterion]
