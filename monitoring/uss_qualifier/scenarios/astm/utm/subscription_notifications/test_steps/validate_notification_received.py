from datetime import datetime

from implicitdict import StringBasedDateTime
from uas_standards.astm.f3548.v21.api import OperationID

from monitoring.monitorlib.clients.mock_uss.interactions import QueryDirection
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.wait import (
    wait_in_intervals,
)
from monitoring.uss_qualifier.scenarios.interuss.mock_uss.test_steps import (
    base_url_filter,
    direction_filter,
    get_mock_uss_interactions,
    notif_op_intent_id_filter,
    notif_sub_id_filter,
    operation_filter,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


def expect_tested_uss_receives_notification_from_mock_uss(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    interactions_since_time: datetime,
    op_intent_ref_id: str,
    subscription_id: str,
    tested_uss_base_url: str,
    tested_uss_participant_id: str,
    plan_request_time: datetime,
):
    """
    This step checks if expected notification was received by tested_uss from mock_uss.
    As it could take time for the notification to be sent, this function will poll for the notifications,
    till a max time is reached.
    Args:
        interactions_since_time: the earliest time a notification may have been sent
        op_intent_ref_id: expected operational_intent_id in the notification
        subscription_id: expected subscription_id in the notification
        tested_uss_base_url: base_url of tested_uss to which the notification should be sent
        tested_uss_participant_id: participant_id of the tested_uss receiving the notification
        plan_request_time: timestamp of the mock_uss flight plan query that would lead to sending notification
    """

    # Check for Mock USS interactions (with notifications) in intervals till max wait time reached

    with scenario.check(
        "Mock USS sends valid notification", mock_uss.participant_id
    ) as check:
        interactions, query = wait_in_intervals(get_mock_uss_interactions)(
            scenario,
            mock_uss,
            StringBasedDateTime(interactions_since_time),
            operation_filter(OperationID.NotifyOperationalIntentDetailsChanged),
            direction_filter(QueryDirection.Outgoing),
            notif_op_intent_id_filter(op_intent_ref_id),
            notif_sub_id_filter(subscription_id),
            base_url_filter(tested_uss_base_url),
        )
        if not interactions:
            check.record_failed(
                summary="No valid notification sent by mock_uss to tested_uss",
                details=f"Notification not sent for intent id {op_intent_ref_id} to tested_uss url {tested_uss_base_url} with subscription id {subscription_id}, even though DSS instructed mock_uss to notify tested_uss based on subscription associated with its relevant operational intent.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )
            return  # no use in continuing if the mock USS does not behave as expected
        elif len(interactions) > 1:
            check.record_failed(
                summary="Too many notifications sent by mock_uss to tested_uss",
                details=f"Too many notifications were sent for intent id {op_intent_ref_id} to tested_uss url {tested_uss_base_url} with subscription id {subscription_id}.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )
            return  # no use in continuing if the mock USS does not behave as expected

    with scenario.check(
        "Tested USS receives valid notification", [tested_uss_participant_id]
    ) as check:
        resp_status = interactions[0].query.response.status_code
        if resp_status != 204:
            check.record_failed(
                summary="Valid notification not accepted by tested_uss.",
                details=f"Valid notification by mock_uss not accepted by tested_uss. Tested_uss responded with response status {resp_status} instead of 204.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )
