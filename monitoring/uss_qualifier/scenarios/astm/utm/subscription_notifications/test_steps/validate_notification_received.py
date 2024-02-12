import arrow
from implicitdict import StringBasedDateTime, ImplicitDict

from typing import Callable, List, Tuple
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from datetime import datetime, timedelta
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.expected_interactions_test_steps import (
    mock_uss_interactions,
)
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.constants import (
    MaxTimeToWaitForSubscriptionNotificationSeconds as max_wait_time,
)
from monitoring.monitorlib.clients.mock_uss.interactions import Interaction
from monitoring.monitorlib.clients.mock_uss.interactions import QueryDirection
from uas_standards.astm.f3548.v21.api import (
    OperationID,
    PutOperationalIntentDetailsParameters,
)


def expect_tested_uss_receives_notification_from_mock_uss(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    op_intent_ref_id: str,
    subscription_id: str,
    tested_uss_domain: str,
    tested_uss_participant_id: str,
    plan_request_time: datetime,
):
    """
    This step checks if expected notification was received by tested_uss from mock_uss
    Args:
        st: the earliest time a notification may have been sent
        op_intent_ref_id: expected operational_intent_id in the notification
        subscription_id: expected subscription_id in the notification
        tested_uss_domain: url domain of tested_uss to which the notification should be sent
        tested_uss_participant_id: participant_id of the tested_uss receiving the notification
        plan_request_time: timestamp of the mock_uss flight plan query that would lead to sending notification
    """

    wait_until = arrow.utcnow().datetime + timedelta(seconds=max_wait_time)
    while arrow.utcnow().datetime < wait_until:
        interactions, query = mock_uss_interactions(
            scenario=scenario,
            mock_uss=mock_uss,
            op_id=OperationID.NotifyOperationalIntentDetailsChanged,
            direction=QueryDirection.Outgoing,
            since=st,
            is_applicable=is_notification_sent_to_url_with_op_intent_id(
                op_intent_ref_id, tested_uss_domain
            ),
        )

    #  Check if a notification exists with expected subscription_id, in the interactions
    (
        notification_with_subscr_id_sent,
        resp_status,
    ) = _check_notification_exists_with_subscription_id(interactions, subscription_id)

    with scenario.check(
        "Mock USS sends valid notification", mock_uss.participant_id
    ) as check:
        if not interactions:
            check.record_failed(
                summary=f"No notification sent to tested_uss",
                details=f"Notification to tested_uss with pre-existing relevant operational intent not sent even though DSS instructed mock_uss to notify due to subscription.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )
        if interactions and not notification_with_subscr_id_sent:
            check.record_failed(
                summary=f"Notification sent with invalid subscriptions by mock_uss",
                details=f"Notification sent to tested_uss with pre-existing relevant operational intent, did not contain the expected subscription_id.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )

    with scenario.check(
        "Tested USS receives valid notification", [tested_uss_participant_id]
    ) as check:
        if notification_with_subscr_id_sent and resp_status != 200:
            check.record_failed(
                summary=f"Valid notification not accepted by tested_uss.",
                details=f"Valid notification by mock_uss not accepted by tested_uss. Tested_uss should have responded with status 200.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )

    with scenario.check(
        "Tested USS rejects invalid notification"[tested_uss_participant_id]
    ) as check:
        if interactions and not notification_with_subscr_id_sent and resp_status != 400:
            check.record_failed(
                summary=f"Invalid notification should be rejected",
                details=f"Invalid notification containing incorrect subscription_id should be rejected by tested_uss, with response status 400.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )


def is_notification_sent_to_url_with_op_intent_id(
    op_intent_id: str,
    url_domain: str,
) -> Callable[[Interaction], bool]:
    """
    Returns an `is_applicable` function that detects if the request in an interaction is sent to the given url and with given op_intent_id

    Args:
        op_intent_id: The operational_intent id that needs to be notified
        url_domain: The url domain to which the notification request needs to be sent

    """

    def is_applicable(interaction: Interaction) -> bool:
        if "json" in interaction.query.request and interaction.query.request.json:
            return (
                interaction.query.request.json.get("operational_intent_id", None)
                == op_intent_id
            ) and (url_domain in interaction.query.request.url_hostname)
        return False

    return is_applicable()


def _check_notification_exists_with_subscription_id(
    interactions: List[Interaction], subscription_id: str
) -> Tuple[bool, int]:
    """
    Check if notifications with subscription_id is found in the given interactions

    Returns:
        exists: True if a notification with subscription_id is found, else False
        status: Response status code for a notification

    """
    exists: bool = False
    status: int = 999
    for interaction in interactions:
        try:
            notification = ImplicitDict.parse(
                interaction.query.request.json, PutOperationalIntentDetailsParameters
            )
            subscriptions = notification.subscriptions
            for subscription in subscriptions:
                if subscription.subscription_id == subscription_id:
                    return True, interaction.query.response.status_code
                else:
                    exists = False
                    status = interaction.query.response.status_code
        except Exception:
            pass

    return exists, status
