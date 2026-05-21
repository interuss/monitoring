from __future__ import annotations

from datetime import datetime

from implicitdict import StringBasedDateTime
from uas_standards.astm.f3548.v21.api import (
    EntityID,
    OperationID,
)

from monitoring.monitorlib.clients.mock_uss.interactions import QueryDirection
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.wait import (
    wait_in_intervals,
)
from monitoring.uss_qualifier.scenarios.interuss.mock_uss.test_steps import (
    direction_filter,
    filter_interactions,
    get_mock_uss_interactions,
    notif_op_intent_id_filter,
    operation_filter,
    status_code_filter,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


def expect_mock_uss_receives_op_intent_notification(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    op_intent_id: EntityID,
    participant_id: str,
    plan_request_time: datetime,
):
    """This step checks if a notification is sent to mock_uss within the required time window.

    Args:
        st: the earliest time a notification may have been sent
        op_intent_id: the operational intent ID subject of the notification
        participant_id: id of the participant responsible to send the notification
        plan_request_time: timestamp of the flight plan query that would lead to sending notification
    """

    # Check for 'notification found' will be done periodically by waiting for a duration till max_wait_time
    found, query = wait_in_intervals(get_mock_uss_interactions, scenario)(
        scenario,
        mock_uss,
        st,
        operation_filter(OperationID.NotifyOperationalIntentDetailsChanged),
        direction_filter(QueryDirection.Incoming),
        notif_op_intent_id_filter(op_intent_id),
        status_code_filter(204),
    )

    with scenario.check("Expect Notification sent", [participant_id]) as check:
        if not found:
            check.record_failed(
                summary=f"Notification not sent for {op_intent_id}",
                details=f"Notification from {participant_id} to USS for {op_intent_id} with pre-existing relevant operational intent not sent even though DSS instructed the planning USS to notify due to subscription.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )


def expect_no_interuss_post_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    shared_op_intent_ids: set[EntityID],
    participant_id: str,
):
    """This step checks no notification about an unexpected operational intent is sent to any USS within the required time window (as no DSS entity was created).

    Args:
        st: the earliest time a notification may have been sent
        shared_op_intent_ids: the set of IDs of previously shared operational intents for which it is expected that notifications are present regardless of their timings
        participant_id: id of the participant responsible to send the notification
    """
    interactions, query = get_mock_uss_interactions(
        scenario,
        mock_uss,
        st,
        operation_filter(OperationID.NotifyOperationalIntentDetailsChanged),
        direction_filter(QueryDirection.Incoming),
    )

    with scenario.check(
        "Expect Notification not sent", [participant_id]
    ) as no_notification_check:
        for interaction in interactions:
            with scenario.check(
                "Mock USS interaction can be parsed", [mock_uss.participant_id]
            ) as check:
                req = interaction.query.request.json
                if not req or "operational_intent_id" not in req:
                    check.record_failed(
                        summary="Failed to find an operational intent ID within a 'NotifyOperationalIntentDetailsChanged' interaction with mock_uss",
                        details=f"Request: {interaction.query.request.json}",
                        query_timestamps=[query.request.timestamp],
                    )
                    continue  # low priority failure: continue checking interactions if one cannot be parsed

                op_intent_id = EntityID(req.get("operational_intent_id"))
                if op_intent_id not in shared_op_intent_ids:
                    no_notification_check.record_failed(
                        summary=f"Observed unexpected notification for operational intent ID {op_intent_id}.",
                        details=f"Notification for operational intent ID {op_intent_id} triggered by subscriptions {req.get('subscriptions', None)}.",
                        query_timestamps=[query.request.timestamp],
                    )


def expect_uss_obtained_op_intent_details(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    op_intent_id: EntityID,
    participant_id: str,
):
    """
    This step verifies that a USS obtained operational intent details from a Mock USS by means of either a notification
    from the Mock USS (push), or a GET request (operation *getOperationalIntentDetails*) to the Mock USS.

    Implements the test step fragment in `validate_operational_intent_details_obtained.md`.

    Args:
        st: the earliest time a notification may have been sent
        op_intent_id: the operational intent ID subject of the notification
        participant_id: id of the participant responsible to obtain the details
    """

    all_interactions, query = get_mock_uss_interactions(
        scenario,
        mock_uss,
        st,
    )

    notifications = filter_interactions(
        all_interactions,
        [
            operation_filter(OperationID.NotifyOperationalIntentDetailsChanged),
            direction_filter(QueryDirection.Outgoing),
            notif_op_intent_id_filter(op_intent_id),
            status_code_filter(204),
        ],
    )

    get_requests = filter_interactions(
        all_interactions,
        [
            operation_filter(
                OperationID.GetOperationalIntentDetails, entityid=op_intent_id
            ),
            direction_filter(QueryDirection.Incoming),
            status_code_filter(200),
        ],
    )

    with scenario.check(
        "USS obtained operational intent details by means of either notification or GET request",
        [participant_id],
    ) as check:
        if not notifications and not get_requests:
            check.record_failed(
                summary=f"USS {participant_id} did not obtained details of operational intent {op_intent_id} from mock_uss",
                details=f"operational intent {op_intent_id}: mock_uss did not notify successfully {participant_id} of the details and {participant_id} did not do a successful GET request to retrieve them either since {st}",
                query_timestamps=[query.request.timestamp],
            )
