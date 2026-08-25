from typing import Optional

from implicitdict import ImplicitDict, StringBasedTimeDelta
from uas_standards.astm.f3548.v21.api import SubscriptionID

from monitoring.benchmarker.configurations.actions.astm import (
    SubscriptionCreationMode,
    SubscriptionDeletionMode,
)
from monitoring.monitorlib.geo import Altitude, LatLngBoundingBox


class Subscription(ImplicitDict):
    subscription_id: SubscriptionID
    """ID of the single subscription to create."""

    duration: StringBasedTimeDelta
    """Duration of the subscription, from the time it is created."""

    area: LatLngBoundingBox
    """Horizontal area this subscription should cover."""

    min_alt: Altitude
    """Altitude below which this subscription should not apply."""

    max_alt: Altitude
    """Altitude above which this subscription should not apply."""

    notify_for_op_intents: Optional[bool]
    """Whether to receive notifications for operational intents. Defaults to True if not specified."""

    notify_for_constraints: Optional[bool]
    """Whether to receive notifications for constraints. Defaults to False if not specified."""


class CreateSubscription(ImplicitDict):
    """Create a subscription."""

    subscription: Subscription
    """Characteristics of subscription to create."""

    mode: SubscriptionCreationMode
    """Desired creation behavior."""


class DeleteSubscription(ImplicitDict):
    subscription_id: SubscriptionID
    """ID of the subscription to delete."""

    mode: SubscriptionDeletionMode
    """Desired deletion behavior."""


class F3548ActionSpecification(ImplicitDict):
    """Actions pertaining to ASTM F3548 SCD."""

    create_subscription: Optional[CreateSubscription]
    delete_subscription: Optional[DeleteSubscription]
