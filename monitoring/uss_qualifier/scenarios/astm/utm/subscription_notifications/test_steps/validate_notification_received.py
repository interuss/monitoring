from implicitdict import StringBasedDateTime, ImplicitDict
from typing import List, Tuple

from monitoring.uss_qualifier.scenarios.interuss.mock_uss.test_steps import (
    get_mock_uss_interactions,
    operation_filter,
    direction_filter,
    notif_op_intent_id_filter,
    base_url_filter,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from datetime import datetime
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.wait import (
    wait_in_intervals,
)
from monitoring.monitorlib.clients.mock_uss.interactions import (
    Interaction,
    QueryDirection,
)
from uas_standards.astm.f3548.v21.api import (
    OperationID,
    PutOperationalIntentDetailsParameters,
)


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
        try:
            interactions, query = wait_in_intervals(get_mock_uss_interactions)(
                scenario,
                mock_uss,
                StringBasedDateTime(interactions_since_time),
                operation_filter(OperationID.NotifyOperationalIntentDetailsChanged),
                direction_filter(QueryDirection.Outgoing),
                notif_op_intent_id_filter(op_intent_ref_id),
                base_url_filter(tested_uss_base_url),
            )
        except ValueError as e:
            check.record_failed(
                summary=f"Invalid notification sent by mock_uss to tested_uss",
                details=f"Notification to tested_uss sent in invalid format. {str(e)}\n\nStack trace:\n{e.stacktrace}",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )
        if not interactions:
            check.record_failed(
                summary=f"No notification sent by mock_uss to tested_uss",
                details=f"Notification not sent for intent id {op_intent_ref_id} to tested_uss url {tested_uss_base_url}, even though DSS instructed mock_uss to notify tested_uss based on subscription associated with its relevant operational intent.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )

        #  Check if a notification with expected subscription_id exists in the interactions
        (
            is_subscr_id_in_notification,
            resp_status,
        ) = _check_notification_sent_with_subscription_id_and_response(
            interactions, subscription_id
        )

        if interactions and not is_subscr_id_in_notification:
            check.record_failed(
                summary=f"Invalid notification sent by mock_uss",
                details=f"Notification to tested_uss missing the subscription_id ({subscription_id}), of the operational intent owned by tested_uss .",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )

    if is_subscr_id_in_notification:
        with scenario.check(
            "Tested USS receives valid notification", [tested_uss_participant_id]
        ) as check:
            if resp_status != 204:
                check.record_failed(
                    summary=f"Valid notification not accepted by tested_uss.",
                    details=f"Valid notification by mock_uss not accepted by tested_uss. Tested_uss responded with response status {resp_status} instead of 204.",
                    query_timestamps=[plan_request_time, query.request.timestamp],
                )

    if interactions and not is_subscr_id_in_notification:
        with scenario.check(
            "Tested USS rejects invalid notification", [tested_uss_participant_id]
        ) as check:
            if resp_status != 400:
                check.record_failed(
                    summary=f"Invalid notification should be rejected",
                    details=f"Invalid notification containing incorrect subscription_id should be rejected by tested_uss. Tested_uss responded with response status {resp_status} instead of 400.",
                    query_timestamps=[plan_request_time, query.request.timestamp],
                )


def _check_notification_sent_with_subscription_id_and_response(
    interactions: List[Interaction], subscription_id: str
) -> Tuple[bool, int]:
    """
    This function checks if a notification with subscription_id is found in the given interactions,

    interactions: It is assumed that the interactions passed are notifications in valid format
    subscription_id: The subscription_id that should trigger the notification

    Returns:
        notification_with_subscr_id_found: True if a notification with subscription_id is found, else False
        status: Response status code for a notification

    """
    status: int = 999
    for interaction in interactions:
        notification = ImplicitDict.parse(
            interaction.query.request.json,
            PutOperationalIntentDetailsParameters,
        )

        subscriptions = notification.subscriptions
        for subscription in subscriptions:
            if subscription.subscription_id == subscription_id:
                return True, interaction.query.response.status_code
            else:
                status = interaction.query.response.status_code

    return False, status
