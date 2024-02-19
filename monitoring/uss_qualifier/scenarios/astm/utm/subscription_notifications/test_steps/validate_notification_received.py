import arrow
from implicitdict import StringBasedDateTime, ImplicitDict
from monitoring.monitorlib.delay import sleep
from loguru import logger
from typing import Callable, List, Tuple
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from datetime import datetime, timedelta
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.expected_interactions_test_steps import (
    mock_uss_interactions,
)
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.wait import (
    wait_in_intervals,
)
from monitoring.monitorlib.clients.mock_uss.interactions import (
    Interaction,
    QueryDirection,
)
from monitoring.monitorlib.fetch import QueryType
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
    This step checks if expected notification was received by tested_uss from mock_uss
    Args:
        interactions_since_time: the earliest time a notification may have been sent
        op_intent_ref_id: expected operational_intent_id in the notification
        subscription_id: expected subscription_id in the notification
        tested_uss_base_url: base_url of tested_uss to which the notification should be sent
        tested_uss_participant_id: participant_id of the tested_uss receiving the notification
        plan_request_time: timestamp of the mock_uss flight plan query that would lead to sending notification
    """

    # Check for Mock USS interactions (with notifications) in intervals till max wait time reached
    interactions, query = wait_in_intervals(mock_uss_interactions)(
        scenario=scenario,
        mock_uss=mock_uss,
        op_id=OperationID.NotifyOperationalIntentDetailsChanged,
        direction=QueryDirection.Outgoing,
        since=StringBasedDateTime(interactions_since_time),
        is_applicable=_is_notification_sent_to_url_with_op_intent_id(
            op_intent_ref_id, tested_uss_base_url
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
                summary=f"Invalid notification sent by mock_uss",
                details=f"Invalid notification sent by mock_uss to tested_uss - invalid format or missing subscription_id ({subscription_id}), of the operational intent owned by tested_uss .",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )

    if notification_with_subscr_id_sent and resp_status != 204:
        with scenario.check(
            "Tested USS receives valid notification", [tested_uss_participant_id]
        ) as check:
            check.record_failed(
                summary=f"Valid notification not accepted by tested_uss.",
                details=f"Valid notification by mock_uss not accepted by tested_uss. Tested_uss should have responded with status 200.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )

    if interactions and not notification_with_subscr_id_sent and resp_status != 400:
        with scenario.check(
            "Tested USS rejects invalid notification", [tested_uss_participant_id]
        ) as check:
            check.record_failed(
                summary=f"Invalid notification should be rejected",
                details=f"Invalid notification containing incorrect subscription_id should be rejected by tested_uss, with response status 400.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )


def _is_notification_sent_to_url_with_op_intent_id(
    op_intent_id: str,
    base_url: str,
) -> Callable[[Interaction], bool]:
    """
    Returns an `is_applicable` function that detects if the request in an interaction is sent to the given url and with given op_intent_id

    Args:
        op_intent_id: The operational_intent id that needs to be notified
        base_url: The url domain to which the notification request needs to be sent

    """

    def is_applicable(interaction: Interaction) -> bool:
        if "json" in interaction.query.request and interaction.query.request.json:
            return (
                interaction.query.request.json.get("operational_intent_id", None)
                == op_intent_id
            ) and (base_url in interaction.query.request.url_hostname)
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
        if (
            interaction.query.query_type
            == QueryType.F3548v21USSNotifyOperationalIntentDetailsChanged
        ):
            try:
                notification = ImplicitDict.parse(
                    interaction.query.request.json,
                    PutOperationalIntentDetailsParameters,
                )
            except (ValueError, TypeError, KeyError) as e:
                logger.debug(
                    f"Parsing mock_uss notification to type PutOperationalIntentDetailsParameters failed - {e}"
                )
                return False, interaction.query.response.status_code
            subscriptions = notification.subscriptions
            for subscription in subscriptions:
                if subscription.subscription_id == subscription_id:
                    return True, interaction.query.response.status_code
                else:
                    exists = False
                    status = interaction.query.response.status_code

    return exists, status
