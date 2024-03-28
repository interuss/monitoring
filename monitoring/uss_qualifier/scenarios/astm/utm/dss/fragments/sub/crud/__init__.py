from typing import Tuple, List

from uas_standards.astm.f3548.v21.api import Subscription, OperationalIntentReference

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
