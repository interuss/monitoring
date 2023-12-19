from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Callable, Dict, List, Tuple, Optional
import time

import arrow
from implicitdict import StringBasedDateTime
from loguru import logger
from uas_standards.astm.f3548.v21 import api
from uas_standards.astm.f3548.v21.api import OperationID, EntityID

from monitoring.monitorlib.clients.mock_uss.interactions import Interaction
from monitoring.monitorlib.clients.mock_uss.interactions import QueryDirection
from monitoring.monitorlib.fetch import QueryError, Query
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.constants import (
    MaxTimeToWaitForSubscriptionNotificationSeconds as max_wait_time,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType

# Interval to wait for checking notification received
WAIT_INTERVAL_SECONDS = 1


def expect_mock_uss_receives_op_intent_notification(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    participant_id: str,
    plan_request_time: datetime,
):
    """This step checks if a notification is sent to mock_uss within the required time window.

    Args:
        st: the earliest time a notification may have been sent
        participant_id: id of the participant responsible to send the notification
        plan_request_time: timestamp of the flight plan query that would lead to sending notification
    """

    # Check for 'notification found' will be done periodically by waiting for a duration till max_wait_time
    wait_until = arrow.utcnow().datetime + timedelta(seconds=max_wait_time)
    while arrow.utcnow().datetime < wait_until:
        found, query = mock_uss_interactions(
            scenario=scenario,
            mock_uss=mock_uss,
            op_id=OperationID.NotifyOperationalIntentDetailsChanged,
            direction=QueryDirection.Incoming,
            since=st,
        )
        if found:
            break
        dt = (wait_until - arrow.utcnow().datetime).total_seconds()
        if dt > 0:
            time.sleep(min(dt, WAIT_INTERVAL_SECONDS))

    with scenario.check("Expect Notification sent", [participant_id]) as check:
        if not found:
            check.record_failed(
                summary=f"Notification not sent",
                details=f"Notification to USS with pre-existing relevant operational intent not sent even though DSS instructed the planning USS to notify due to subscription.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )


def expect_no_interuss_post_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    participant_id: str,
):
    """This step checks no notification is sent to any USS within the required time window (as no DSS entity was created).

    Args:
        st: the earliest time a notification may have been sent
        participant_id: id of the participant responsible to send the notification
    """
    # Wait for next MaxTimeToWaitForSubscriptionNotificationSeconds duration to capture any notification
    time.sleep(max_wait_time)
    found, query = mock_uss_interactions(
        scenario=scenario,
        mock_uss=mock_uss,
        op_id=OperationID.NotifyOperationalIntentDetailsChanged,
        direction=QueryDirection.Incoming,
        since=st,
    )
    with scenario.check("Expect Notification not sent", [participant_id]) as check:
        if found:
            check.record_failed(
                summary=f"Notification was wrongly sent for an entity not created.",
                details=f"Notification was wrongly sent for an entity not created.",
                query_timestamps=[query.request.timestamp],
            )


def mock_uss_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    op_id: OperationID,
    direction: QueryDirection,
    since: StringBasedDateTime,
    query_params: Optional[Dict[str, str]] = None,
    is_applicable: Optional[Callable[[Interaction], bool]] = None,
) -> Tuple[List[Interaction], Query]:
    """Determine if mock_uss recorded an interaction for the specified operation in the specified direction."""

    with scenario.check(
        "MockUSS interactions request", [mock_uss.participant_id]
    ) as check:
        try:
            interactions, query = mock_uss.get_interactions(since)
            scenario.record_query(query)
        except QueryError as e:
            for q in e.queries:
                scenario.record_query(q)
            check.record_failed(
                summary=f"Error from mock_uss when attempting to get interactions from_time {st}",
                details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                query_timestamps=[q.request.timestamp for q in e.queries],
            )

    op = api.OPERATIONS[op_id]

    op_path = op.path
    if query_params is None:
        query_params = {}
    for m in re.findall(r"\{[^}]+\}", op_path):
        param_name = m[1:-1]
        op_path = op_path.replace(m, query_params.get(param_name, r"[^/]+"))

    if is_applicable is None:
        is_applicable = lambda i: True
    result = []
    for interaction in interactions:
        if (
            interaction.direction == direction
            and interaction.query.request.method == op.verb
            and re.search(op_path, interaction.query.request.url)
            and is_applicable(interaction)
        ):
            result.append(interaction)
    return result, query


def is_op_intent_notification_with_id(
    op_intent_id: EntityID,
) -> Callable[[Interaction], bool]:
    """Returns an `is_applicable` function that detects whether an op intent notification refers to the specified operational intent."""

    def is_applicable(interaction: Interaction) -> bool:
        if "json" in interaction.query.request and interaction.query.request.json:
            return (
                interaction.query.request.json.get("operational_intent_id", None)
                == op_intent_id
            )
        return False

    return is_applicable
