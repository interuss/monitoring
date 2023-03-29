from __future__ import annotations
from typing import Optional, List

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.requirements.definitions import RequirementCollection


BadgeID = str
"""Identifier of a badge."""

JSONPathExpression = str
"""JsonPath expression; see https://pypi.org/project/jsonpath-ng/"""


class SpecificCondition(ImplicitDict):
    pass


class AllConditions(SpecificCondition):
    """Condition will only be satisfied when all specified conditions are satisfied."""

    conditions: List[BadgeGrantCondition]


class AnyCondition(SpecificCondition):
    """Condition will be satisfied when any of the specified conditions are satisfied."""

    conditions: List[BadgeGrantCondition]


class RequirementsCheckedCondition(SpecificCondition):
    """Condition will only be satisfied if at least one successful check exists for all specified requirements."""

    checked: RequirementCollection
    """Each requirement contained within this collection must be covered by at least one successful check."""


class NoFailedChecksCondition(SpecificCondition):
    """Condition will only be satisfied if there are no applicable failed checks.

    For a badge granted to a participant, only checks including the participant's ID will be considered."""

    pass


class BadgeGrantedCondition(SpecificCondition):
    """Condition will be satisfied when the specified badge is granted."""

    badge_id: BadgeID
    """Identifier of badge that must be granted for this condition to be satisifed."""

    badge_location: Optional[JSONPathExpression]
    """Location of report to inspect for the presence of the specified badge, relative to the report in which the badge
    is defined.  Implicit default value is "$" (look for granted batch in the report in which the dependant badge is
    defined).

    If this location resolves to multiple TestSuiteReports, then the badge must be granted in all resolved reports in
    order for this condition to be satisfied.  When this location resolves to artifacts that are not TestSuiteReports,
    those artifacts will be ignored.

    Note that badges are evaluated in the order they are defined.  So, if badge B defined in a particular location
    depends on whether badge A in that same location is granted, badge A must be defined before badge B is defined.
    Also note that badges are computed as test components are completed.  Since a parent test component (e.g., test
    suite) is not complete until all of its child components are complete, a descendant test component's badge condition
    cannot depend on whether an ancestor's (e.g., parent's) badge is granted.
    """


class BadgeGrantCondition(ImplicitDict):
    """Specification of a single condition used to determine whether a badge should be granted.

    Exactly one field must be specified."""

    all_conditions: Optional[AllConditions]
    any_conditions: Optional[AnyCondition]
    no_failed_checks: Optional[NoFailedChecksCondition]
    requirements_checked: Optional[RequirementsCheckedCondition]
    badge_granted: Optional[BadgeGrantedCondition]


class ParticipantBadgeDefinition(ImplicitDict):
    id: BadgeID
    """Identifier of this badge, unique at the level in which this badge is defined."""

    name: str
    """Human-readable name of the badge"""

    description: str
    """Human-readable description of the achievement granting of the badge indicates."""

    grant_condition: BadgeGrantCondition
    """Condition required in order to grant the badge."""
