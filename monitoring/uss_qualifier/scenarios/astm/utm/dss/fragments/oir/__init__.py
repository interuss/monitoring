from typing import Optional

from uas_standards.astm.f3548.v21.api import EntityID, SubscriptionID

from monitoring.monitorlib.fetch import QueryError
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType

# The InterUSS DSS implementation will set an OIR's subscription ID to 00000000-0000-4000-8000-000000000000
# when the OIR is not attached to any subscription, as the OpenAPI spec does not allow the value to be empty.
# Other implementations may use a different value. One way to check that an OIR is not attached to any subscription
# is to attempt to retrieve the subscription reportedly attached to it: if a 404 is returned then we may assume
# no subscription is attached.
# Note that this is only allowed for OIRs in the ACCEPTED state.
NULL_SUBSCRIPTION_ID = "00000000-0000-4000-8000-000000000000"


def step_oir_has_correct_subscription(
    scenario: TestScenarioType,
    dss: DSSInstance,
    oir_id: EntityID,
    expected_sub_id: Optional[SubscriptionID],
    step_name: Optional[str] = None,
):
    """
    Ensure that an OIR is currently attached to the specified subscription,
    or not attached to any subscription if the passed subscription ID is None.

    If the passed step_name is None, a generic step name will be used depending on if expected_sub_id is defined or not

    This fragment will fetch the OIR from the DSS.
    """

    if step_name is None:
        chosen_step_name = (
            "OIR is not attached to any subscription"
            if expected_sub_id is None
            else "OIR is attached to expected subscription"
        )
    else:
        chosen_step_name = step_name
    scenario.begin_test_step(chosen_step_name)
    check_oir_has_correct_subscription(
        scenario,
        dss,
        oir_id,
        expected_sub_id,
    )
    scenario.end_test_step()


def check_oir_has_correct_subscription(
    scenario: TestScenarioType,
    dss: DSSInstance,
    oir_id: EntityID,
    expected_sub_id: Optional[SubscriptionID],
):
    with scenario.check(
        "Get operational intent reference by ID", dss.participant_id
    ) as check:
        try:
            oir, q = dss.get_op_intent_reference(oir_id)
            scenario.record_query(q)
        except QueryError as qe:
            scenario.record_queries(qe.queries)
            check.record_failed(
                summary="Could not get OIR",
                details=f"Failed to get OIR with error code {qe.cause_status_code}: {qe.msg}",
                query_timestamps=qe.query_timestamps,
            )

    sub_is_as_expected = False
    referenced_sub_was_found_when_non_expected = False
    if expected_sub_id is None:
        if oir.subscription_id is None:
            # Sub ID not set at all: not compliant with the spec, but not wrong with regard to which subscription should be attached to the OIR
            sub_is_as_expected = True
        else:
            # - We expect oir.subscription_id to be defined and set to NULL_SUBSCRIPTION_ID. See comment above NULL_SUBSCRIPTION_ID.
            # ASTM may at some point decide to tolerate accepting empty returned values here,
            # but in the meantime we simply attempt to obtain the subscription and check that it does not exist
            # - If the subscription ID is defined and not set to the known 'null' value, we assume that the DSS used another
            # placeholder for the non-existing subscription.
            # - In all cases, we issue a query to the DSS to check whether the subscription exists or not.
            with scenario.check(
                "Subscription referenced by the OIR does not exist", dss.participant_id
            ) as check:
                sub = dss.get_subscription(oir.subscription_id)
                scenario.record_query(sub)
                if sub.status_code not in [200, 404]:
                    check.record_failed(
                        summary="Failed to try to obtain the subscription referenced by the OIR",
                        details=f"Failed in an unexpected way while querying subscription with ID {oir.subscription_id}: expected a 404 or 200, but got {sub.status_code}",
                        query_timestamps=[sub.request.timestamp],
                    )
                if sub.status_code == 200:
                    referenced_sub_was_found_when_non_expected = True
                if sub.status_code == 404:
                    sub_is_as_expected = True
    else:
        sub_is_as_expected = oir.subscription_id == expected_sub_id

    attached_check_name = (
        "OIR is not attached to a subscription"
        if expected_sub_id is None
        else "OIR is attached to expected subscription"
    )

    with scenario.check(attached_check_name, dss.participant_id) as check:
        if referenced_sub_was_found_when_non_expected:
            check.record_failed(
                summary="OIR is attached to a subscription although it should not be",
                details=f"Expected OIR to not be attached to any subscription, but the referenced subscription {oir.subscription_id} does exist.",
                query_timestamps=[sub.request.timestamp],
            )
        if not sub_is_as_expected:
            check.record_failed(
                summary="OIR is not attached to the correct subscription",
                details=f"Expected OIR to be attached to subscription {expected_sub_id}, but it is attached to {oir.subscription_id}",
                query_timestamps=[q.request.timestamp],
            )
