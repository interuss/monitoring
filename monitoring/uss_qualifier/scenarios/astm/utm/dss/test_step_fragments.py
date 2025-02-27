from typing import Optional

import loguru
from uas_standards.astm.f3548.v21.api import EntityID, Volume4D

from monitoring.monitorlib import fetch
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


def remove_op_intent(
    scenario: TestScenarioType, dss: DSSInstance, oi_id: EntityID, ovn: str
) -> None:
    """Remove the specified operational intent reference from the DSS.

    The specified operational intent reference must be managed by `dss`'s auth adapter subscriber.

    This function implements the test step fragment described in remove_op_intent.md.
    """
    with scenario.check(
        "Operational intent reference removed", dss.participant_id
    ) as check:
        try:
            removed_ref, subscribers_to_notify, query = dss.delete_op_intent(oi_id, ovn)
            scenario.record_query(query)
        except fetch.QueryError as e:
            scenario.record_queries(e.queries)
            query = e.cause
            check.record_failed(
                summary=f"Could not remove op intent reference {oi_id}",
                details=f"When attempting to remove op intent reference {oi_id} from the DSS, received {query.status_code}; {e}",
                query_timestamps=[query.request.timestamp],
            )

    # TODO: Attempt to notify subscribers


def remove_constraint_ref(
    scenario: TestScenarioType, dss: DSSInstance, cr_id: EntityID, ovn: str
) -> None:
    """Remove the specified constraint reference from the DSS.

    The specified constraint reference must be managed by `dss`'s auth adapter subscriber.

    This function implements parts of the test step fragment described in astm/utm/dss/clean_workspace.md.
    """
    with scenario.check("Constraint reference removed", dss.participant_id) as check:
        try:
            removed_ref, subscribers_to_notify, query = dss.delete_constraint_ref(
                cr_id, ovn
            )
            scenario.record_query(query)
        except fetch.QueryError as e:
            scenario.record_queries(e.queries)
            query = e.cause
            check.record_failed(
                summary=f"Could not remove constraint reference {cr_id}",
                details=f"When attempting to remove constraint reference {cr_id} from the DSS, received {query.status_code}; {e}",
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
                details=f"When attempting to query subscription {sub_id} from the DSS, received {existing_sub.status_code}: {existing_sub.error_message}",
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
                details=f"When attempting to delete subscription {sub_id} from the DSS, received {deleted_sub.status_code} with body {deleted_sub.error_message}",
                query_timestamps=[deleted_sub.request.timestamp],
            )

    return deleted_sub


def cleanup_active_subs(
    scenario: TestScenarioType, dss: DSSInstance, volume: Volume4D
) -> None:
    """Search for and delete all active subscriptions at the DSS.

    This function implements the test step fragment described in clean_workspace.md.
    """
    query = dss.query_subscriptions(volume)
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


def cleanup_active_constraint_refs(
    scenario: TestScenarioType,
    dss: DSSInstance,
    volume: Volume4D,
    manager_identity: str,
) -> None:
    """
    Search for and delete all active constraint references at the DSS.

    This function implements some of the test step fragment described in clean_workspace.md:
      - Constraint references can be searched for
      - Constraint reference removed
    """
    with scenario.check(
        "Constraint references can be searched for", [dss.participant_id]
    ) as check:
        try:
            crs, query = dss.find_constraint_ref(volume)
            scenario.record_query(query)
        except QueryError as qe:
            scenario.record_queries(qe.queries)
            check.record_failed(
                summary="Failed to query constraint references",
                details=f"Failed to query constraint references: got response code {qe.cause.status_code}",
                query_timestamps=[qe.cause.request.timestamp],
            )
            return

    for cr in crs:
        if cr.manager == manager_identity:
            remove_constraint_ref(scenario, dss, cr.id, cr.ovn)


def cleanup_active_oirs(
    scenario: TestScenarioType,
    dss: DSSInstance,
    volume: Volume4D,
    manager_identity: str,
) -> None:
    with scenario.check(
        "Operational intent references can be searched for", [dss.participant_id]
    ) as check:
        try:
            oirs, query = dss.find_op_intent(volume)
            scenario.record_query(query)
        except QueryError as qe:
            scenario.record_queries(qe.queries)
            check.record_failed(
                summary=f"Failed OIR search with HTTP code {qe.cause.status_code}",
                details=f"Failed to query operational intent references: {qe}",
                query_timestamps=[qe.cause.request.timestamp],
            )
            return

        for oir in oirs:
            if oir.manager == manager_identity:
                remove_op_intent(scenario, dss, oir.id, oir.ovn)


def cleanup_op_intent(
    scenario: TestScenarioType, dss: DSSInstance, oi_id: EntityID
) -> None:
    """Remove the specified operational intent reference from the DSS, if it exists."""

    with scenario.check(
        "Operational intent references can be queried by ID", [dss.participant_id]
    ) as check:
        try:
            oir, q = dss.get_op_intent_reference(oi_id)
            scenario.record_query(q)
        except fetch.QueryError as e:
            scenario.record_queries(e.queries)
            if e.cause_status_code != 404:
                check.record_failed(
                    summary="OIR Get query returned code different from 200 or 404",
                    details=e.msg,
                    query_timestamps=e.query_timestamps,
                )
            else:
                return

    remove_op_intent(scenario, dss, oi_id, oir.ovn)


def cleanup_constraint_ref(
    scenario: TestScenarioType, dss: DSSInstance, cr_id: EntityID
) -> None:
    """
    Remove the specified constraint reference from the DSS, if it exists.

    This function implements some of the test step fragment described in clean_workspace.md:
        - Constraint references can be queried by ID
        - Constraint reference removed
    """

    with scenario.check(
        "Constraint references can be queried by ID", [dss.participant_id]
    ) as check:
        try:
            cr, q = dss.get_constraint_ref(cr_id)
            scenario.record_query(q)
        except fetch.QueryError as e:
            scenario.record_queries(e.queries)
            if e.cause_status_code != 404:
                check.record_failed(
                    summary="CR Get query returned code different from 200 or 404",
                    details=e.msg,
                    query_timestamps=e.query_timestamps,
                )
            else:
                return

    remove_constraint_ref(scenario, dss, cr_id, cr.ovn)
