from typing import List, Tuple

from uas_standards.astm.f3548.v21.api import (
    EntityID,
    OperationalIntentReference,
    PutOperationalIntentReferenceParameters,
    SubscriberToNotify,
)

from monitoring.monitorlib.fetch import Query, QueryError
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


def create_oir_query(
    scenario: TestScenarioType,
    dss: DSSInstance,
    oir_id: EntityID,
    oir_params: PutOperationalIntentReferenceParameters,
) -> Tuple[
    OperationalIntentReference,
    List[SubscriberToNotify],
    Query,
]:
    """
    Issue a request to create an OIR to the DSS instance, wrapped in a check documented in `create_query.md`.
    """
    sub_id = oir_params.subscription_id if "subscription_id" in oir_params else None
    with scenario.check(
        "Create operational intent reference query succeeds",
        dss.participant_id,
    ) as check:
        try:
            new_oir, subs, query = dss.put_op_intent(
                extents=oir_params.extents,
                key=oir_params.key,
                state=oir_params.state,
                base_url=oir_params.uss_base_url,
                oi_id=oir_id,
                subscription_id=sub_id,
            )
            scenario.record_query(query)
            return new_oir, subs, query
        except QueryError as qe:
            scenario.record_queries(qe.queries)
            check.record_failed(
                summary="Could not create operational intent reference",
                details=f"Failed to create operational intent reference with error code {qe.cause_status_code}: {qe.msg}",
                query_timestamps=qe.query_timestamps,
            )
            # Failure of the query has a severity that will interrupt the test:
            # no need to return anything


def update_oir_query(
    scenario: TestScenarioType,
    dss: DSSInstance,
    oir_id: EntityID,
    oir_params: PutOperationalIntentReferenceParameters,
    ovn: str,
) -> Tuple[
    OperationalIntentReference,
    List[SubscriberToNotify],
    Query,
]:
    """
    Issue a request to mutate an OIR to the DSS instance, wrapped in a check documented in `update_query.md`.
    """
    sub_id = oir_params.subscription_id if "subscription_id" in oir_params else None
    with scenario.check(
        "Mutate operational intent reference query succeeds",
        dss.participant_id,
    ) as check:
        try:
            updated_oir, subs, query = dss.put_op_intent(
                extents=oir_params.extents,
                key=oir_params.key,
                state=oir_params.state,
                base_url=oir_params.uss_base_url,
                oi_id=oir_id,
                subscription_id=sub_id,
                ovn=ovn,
            )
            scenario.record_query(query)
            return updated_oir, subs, query
        except QueryError as qe:
            scenario.record_queries(qe.queries)
            check.record_failed(
                summary="OIR Mutation with correct OVN failed for unexpected reason",
                details=f"Was expecting an 200 or 201 response because of an incorrect OVN, but got {qe.cause_status_code} instead",
                query_timestamps=qe.query_timestamps,
            )
            # Failure of the query has a severity that will interrupt the test:
            # no need to return anything


def delete_oir_query(
    scenario: TestScenarioType, dss: DSSInstance, oir_id: EntityID, ovn: str
) -> Tuple[OperationalIntentReference, List[SubscriberToNotify], Query]:
    """Issue a request to delete an OIR to the DSS instance, wrapped in a check documented in `delete_query.md`."""
    with scenario.check(
        "Delete operational intent reference query succeeds", dss.participant_id
    ) as check:
        try:
            deleted_oir, subs, query = dss.delete_op_intent(oir_id, ovn)
            scenario.record_query(query)
            return deleted_oir, subs, query
        except QueryError as qe:
            scenario.record_queries(qe.queries)
            check.record_failed(
                summary="Could not delete operational intent reference",
                details=f"Failed to delete operational intent reference with error code {qe.cause_status_code}: {qe.msg}",
                query_timestamps=qe.query_timestamps,
            )
            # Failure of the query has a severity that will interrupt the test:
            # no need to return anything
