from __future__ import annotations
from typing import Optional, List

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.requirements.definitions import RequirementCollection


CapabilityID = str
"""Identifier of a capability that uss_qualifier can verify."""

JSONPathExpression = str
"""JsonPath expression; see https://pypi.org/project/jsonpath-ng/"""
# TODO: Change type to JSONAddress where applicable following merging of #171


class SpecificCondition(ImplicitDict):
    pass


class AllConditions(SpecificCondition):
    """Condition will only be satisfied when all specified conditions are satisfied.

    Note that an empty list of conditions will result in a successful evaluation."""

    conditions: List[CapabilityVerificationCondition]


class AnyCondition(SpecificCondition):
    """Condition will be satisfied when any of the specified conditions are satisfied.

    Note that an empty list of conditions will result in an unsuccessful evaluation."""

    conditions: List[CapabilityVerificationCondition]


class RequirementsCheckedCondition(SpecificCondition):
    """Condition will only be satisfied if at least one successful check exists for all specified requirements.

    Note that an empty collection of requirements will result in an unsuccessful evaluation."""

    checked: RequirementCollection
    """Each requirement contained within this collection must be covered by at least one successful check."""


class NoFailedChecksCondition(SpecificCondition):
    """Condition will only be satisfied if there are no applicable failed checks.

    For a capability to be verified for a participant, only checks including the participant's ID will be considered."""

    pass


class CapabilityVerifiedCondition(SpecificCondition):
    """Condition will be satisfied when the specified capability is verified.

    Note that a capability which do not declare any requirement will result in an unsuccessful evaluation."""

    capability_ids: List[CapabilityID]
    """List of identifier of capability that must be verified for this condition to be satisfied."""

    capability_location: Optional[JSONPathExpression]
    """Location of report to inspect for the verification of the specified capability, relative to the report in which
    the capability is defined.  Implicit default value is "$" (look for verified capability in the report in which the
    dependant capability is defined).

    If this location resolves to multiple TestSuiteReports, then the capability must be verified in all resolved reports
    in order for this condition to be satisfied.  When this location resolves to artifacts that are not
    TestSuiteReports, those artifacts will be ignored.

    Note that capabilities are verified in the order they are defined.  So, if capability B defined in a particular
    location depends on whether capability A in that same location is granted, capability A must be defined before
    capability B is defined.  Also note that capability verifications are computed as test components are completed.
    Since a parent test component (e.g., test suite) is not complete until all of its child components are complete, a
    descendant test component's capability condition cannot depend on whether an ancestor's (e.g., parent's) capability
    is verified.
    """


class CapabilityVerificationCondition(ImplicitDict):
    """Specification of a single condition used to determine whether a capability should be verified.

    Exactly one field must be specified."""

    all_conditions: Optional[AllConditions]
    any_conditions: Optional[AnyCondition]
    no_failed_checks: Optional[NoFailedChecksCondition]
    requirements_checked: Optional[RequirementsCheckedCondition]
    capability_verified: Optional[CapabilityVerifiedCondition]


class ParticipantCapabilityDefinition(ImplicitDict):
    id: CapabilityID
    """Identifier of this capability, unique at the level in which this capability is defined."""

    name: str
    """Human-readable name of the capability."""

    description: str
    """Human-readable description of the capability."""

    verification_condition: CapabilityVerificationCondition
    """Condition required in order to verify the capability."""
