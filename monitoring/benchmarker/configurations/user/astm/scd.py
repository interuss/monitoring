from typing import Optional

from implicitdict import ImplicitDict, StringBasedTimeDelta
from uas_standards.astm.f3548.v21.api import SubscriptionID

from monitoring.benchmarker.configurations.user.astm.dss import ASTMDSSSelectionStrategy
from monitoring.benchmarker.engine.coordination import CoordinationGroupID
from monitoring.uss_qualifier.resources.definitions import ResourceID


class SingleSubscription(ImplicitDict):
    subscription_id: SubscriptionID
    """ID of the single subscription to use when creating operational intents."""


class ImplicitSubscription(ImplicitDict):
    pass


class SubscriptionStrategy(ImplicitDict):
    single_subscription: Optional[SingleSubscription]
    """Planner expects there to be a single subscription established at the start of operations covering all their flights.
    
    A configuration specifying this strategy must separately ensure this subscription exists, such as via an f3548.create_subscription action."""

    implicit_subscription: Optional[ImplicitSubscription]
    """Planner has the DSS establish an implicit subscription for each individual flight."""


class OpIntentRefCreationStrategy(ImplicitDict):
    ovn_coordination_group: Optional[CoordinationGroupID]
    """If specified, exchange OVNs directly between other virtual users using this coordination group to exchange OVNs."""

    coordinate_requested_ovns: Optional[bool]
    """If specified true, use requested OVNs and share them with the coordination group before requesting."""

    retries: Optional[int]
    """If specified, number of times to retry failed operational intent operations before giving up."""

    accept_before_flight_start: Optional[StringBasedTimeDelta]
    """Create an operational intent in the Accepted state this long before the flight starts (start of first volume)."""

    activate_before_flight_start: Optional[StringBasedTimeDelta]
    """Create or update an operational intent to the Activated state this long before the flight starts (start of first volume)."""

    expect_timely_clearance: Optional[bool]
    """If true, fail the flight if acceptance and activation (when specified) are not complete by the start time of the flight."""


class OpIntentRefCleanupStrategy(ImplicitDict):
    after_actual_flight_end: Optional[StringBasedTimeDelta]
    """Delete operational intent reference this amount of time after the actual end of the flight."""

    after_planned_flight_end: Optional[StringBasedTimeDelta]
    """Delete operational intent reference this amount of time after the planned end of the flight (end of last volume)."""


class BehaviorSpecification(ImplicitDict):
    dss_pool: list[ResourceID]
    """Means to interact with the ASTM DSS.
    
    Benchmark configuration must contain a `resources.astm.f3548.v21.DSSInstanceResource` resource with each of these names."""

    dss_selection_strategy: Optional[ASTMDSSSelectionStrategy]

    subscription_strategy: SubscriptionStrategy

    op_intent_ref_creation_strategy: OpIntentRefCreationStrategy

    op_intent_ref_cleanup_strategy: OpIntentRefCleanupStrategy
