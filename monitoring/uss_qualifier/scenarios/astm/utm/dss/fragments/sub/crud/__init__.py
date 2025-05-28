from typing import List, Tuple

from uas_standards.astm.f3548.v21.api import OperationalIntentReference, Subscription

from monitoring.monitorlib.fetch.rid import FetchedSubscription
from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.astm.f3548.v21.subscription_params import (
    SubscriptionParams,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType

# TODO: add functions implementing checks documented in this package


def sub_create_query(
    scenario: TestScenarioType,
    dss: DSSInstance,
    sub_params: SubscriptionParams,
) -> Tuple[Subscription, List[OperationalIntentReference], MutatedSubscription]:
    """Implements check documented in `create_query.md`."""
    with scenario.check(
        "Create subscription query succeeds",
        [dss.participant_id],
    ) as check:
        sub = dss.upsert_subscription(
            **sub_params,
        )
        scenario.record_query(sub)
        if not sub.success:
            check.record_failed(
                summary="Create subscription query failed",
                details=f"Failed to create a subscription on DSS instance with code {sub.status_code}: {sub.error_message}",
                query_timestamps=[sub.request.timestamp],
            )
        return sub.subscription, sub.operational_intent_references, sub


def sub_get_query(
    scenario: TestScenarioType,
    dss: DSSInstance,
    sub_id: str,
) -> Tuple[Subscription, FetchedSubscription]:
    with scenario.check("Get Subscription by ID", dss.participant_id) as check:
        fetched_sub = dss.get_subscription(sub_id)
        scenario.record_query(fetched_sub)
        if fetched_sub.status_code != 200:
            check.record_failed(
                summary="Subscription query failed",
                details=f"Failed to query subscription {sub_id} referenced by oid {self._oir_a_id} with code {fetched_sub.response.status_code}. Message: {fetched_sub.error_message}",
                query_timestamps=fetched_sub.query_timestamps,
            )
            return None

        return fetched_sub.subscription, fetched_sub


def sub_delete_query(
    scenario: TestScenarioType,
    dss: DSSInstance,
    sub_id: str,
    sub_version: str,
) -> Tuple[Subscription, List[OperationalIntentReference], MutatedSubscription]:
    """Implements check documented in `delete_query.md`."""
    with scenario.check(
        "Subscription can be deleted",
        [dss.participant_id],
    ) as check:
        sub = dss.delete_subscription(sub_id, sub_version)
        scenario.record_query(sub)
        if not sub.success:
            check.record_failed(
                summary="Delete subscription query failed",
                details=f"Failed to delete a subscription on DSS instance with code {sub.status_code}: {sub.error_message}",
                query_timestamps=[sub.request.timestamp],
            )
        return sub.subscription, sub.operational_intent_references, sub
