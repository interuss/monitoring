from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from uas_standards.astm.f3548.v21.api import EntityID


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
