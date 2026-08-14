from typing import Optional

from implicitdict import ImplicitDict, StringBasedTimeDelta

from monitoring.benchmarker.configurations.actions.astm import (
    SubscriptionCreationMode,
    SubscriptionDeletionMode,
)
from monitoring.monitorlib.geo import Altitude, LatLngBoundingBox
from monitoring.monitorlib.rid import RIDVersion


class Subscription(ImplicitDict):
    subscription_id: str
    """ID of the single subscription to create."""

    rid_version: RIDVersion

    duration: StringBasedTimeDelta
    """Duration of the subscription, from the time it is created."""

    area: LatLngBoundingBox
    """Horizontal area this subscription should cover."""

    min_alt: Altitude
    """Altitude below which this subscription should not apply."""

    max_alt: Altitude
    """Altitude above which this subscription should not apply."""


class CreateSubscription(ImplicitDict):
    """Create a subscription."""

    subscription: Subscription
    """Characteristics of subscription to create."""

    mode: SubscriptionCreationMode
    """Desired creation behavior."""


class DeleteSubscription(ImplicitDict):
    subscription_id: str
    """ID of the subscription to delete."""

    mode: SubscriptionDeletionMode
    """Desired deletion behavior."""


class F3411ActionSpecification(ImplicitDict):
    """Actions pertaining to ASTM F3411 NetRID."""

    create_subscription: Optional[CreateSubscription]
    delete_subscription: Optional[DeleteSubscription]
