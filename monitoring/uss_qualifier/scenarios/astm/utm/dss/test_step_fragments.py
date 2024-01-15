from typing import Optional

import loguru

from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from uas_standards.astm.f3548.v21.api import EntityID, Volume4D


def remove_op_intent(
    scenario: TestScenarioType, dss: DSSInstance, oi_id: EntityID, ovn: str
) -> None:
    """Remove the specified operational intent reference from the DSS.

    The specified operational intent reference must be managed by `dss`'s auth adapter subscriber.

    This function implements the test step fragment described in remove_op_intent.md.
    """
    removed_ref, subscribers_to_notify, query = dss.delete_op_intent(oi_id, ovn)
    scenario.record_query(query)

    with scenario.check(
        "Operational intent reference removed", dss.participant_id
    ) as check:
        if removed_ref is None:
            check.record_failed(
                summary=f"Could not remove op intent reference {oi_id}",
                details=f"When attempting to remove op intent reference {oi_id} from the DSS, received {query.status_code}",
                query_timestamps=[query.request.timestamp],
            )

    # TODO: Attempt to notify subscribers


def cleanup_sub(
    scenario: TestScenarioType, dss: DSSInstance, sub_id: EntityID
) -> Optional[MutatedSubscription]:
    """Cleanup a subscription at the DSS. Does not fail if it is not found.

    :return: the DSS response if the subscription exists
    """
    existing_sub = dss.get_subscription(sub_id)
    scenario.record_query(existing_sub)
    with scenario.check(
        "Subscription can be queried by ID", [dss.participant_id]
    ) as check:
        if existing_sub.status_code not in [200, 404]:
            check.record_failed(
                summary=f"Could not query subscription {sub_id}",
                details=f"When attempting to query subscription {sub_id} from the DSS, received {existing_sub.status_code}",
                query_timestamps=[existing_sub.request.timestamp],
            )

    if existing_sub.status_code != 200:
        return None

    deleted_sub = dss.delete_subscription(sub_id, existing_sub.subscription.version)
    scenario.record_query(deleted_sub)
    with scenario.check("Subscription can be deleted", [dss.participant_id]) as check:
        if deleted_sub.status_code != 200:
            check.record_failed(
                summary=f"Could not delete subscription {sub_id}",
                details=f"When attempting to delete subscription {sub_id} from the DSS, received {deleted_sub.status_code}",
                query_timestamps=[deleted_sub.request.timestamp],
            )

    return deleted_sub


def cleanup_active_subs(
    scenario: TestScenarioType, dss: DSSInstance, volume: Volume4D
) -> None:
    """Search for and delete all active subscriptions at the DSS.

    This function implements the test step fragment described in search_and_delete_active_subs.md.
    """
    query = dss.search_subscriptions(volume)
    scenario.record_query(query)
    with scenario.check(
        "Successful subscription search query", [dss.participant_id]
    ) as check:
        if query.status_code != 200:
            check.record_failed(
                summary="Could not query subscriptions",
                details=f"When attempting to query subscriptions from the DSS, received {query.status_code}",
                query_timestamps=[query.request.timestamp],
            )

    for sub_id in query.subscriptions.keys():
        cleanup_sub(scenario, dss, sub_id)
