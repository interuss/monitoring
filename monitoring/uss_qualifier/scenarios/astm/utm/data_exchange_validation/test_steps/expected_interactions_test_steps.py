from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Callable, Dict, List, Tuple, Optional, Set

import arrow
from implicitdict import StringBasedDateTime, ImplicitDict
from uas_standards.astm.f3548.v21 import api
from uas_standards.astm.f3548.v21.api import (
    OperationID,
    EntityID,
    PutOperationalIntentDetailsParameters,
    OperationalIntentReference,
)

from monitoring.monitorlib.clients.mock_uss.interactions import Interaction
from monitoring.monitorlib.clients.mock_uss.interactions import QueryDirection
from monitoring.monitorlib.delay import sleep
from monitoring.monitorlib.fetch import QueryError, Query
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.wait import (
    wait_in_intervals,
    MaxTimeToWaitForSubscriptionNotificationSeconds as max_wait_time,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


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
    found, query = wait_in_intervals(mock_uss_interactions)(
        scenario,
        mock_uss,
        st,
        operation_filter(OperationID.NotifyOperationalIntentDetailsChanged),
        direction_filter(QueryDirection.Incoming),
    )

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
    shared_op_intent_ids: Set[EntityID],
    participant_id: str,
):
    """This step checks no notification about an unexpected operational intent is sent to any USS within the required time window (as no DSS entity was created).

    Args:
        st: the earliest time a notification may have been sent
        shared_op_intent_ids: the set of IDs of previously shared operational intents for which it is expected that notifications are present regardless of their timings
        participant_id: id of the participant responsible to send the notification
    """
    sleep(
        max_wait_time,
        "we have to wait the longest it may take a USS to send a notification before we can establish that they didn't send a notification",
    )
    interactions, query = mock_uss_interactions(
        scenario,
        mock_uss,
        st,
        operation_filter(OperationID.NotifyOperationalIntentDetailsChanged),
        direction_filter(QueryDirection.Incoming),
    )

    for interaction in interactions:
        with scenario.check(
            "Mock USS interaction can be parsed", [mock_uss.participant_id]
        ) as check:
            try:
                req = PutOperationalIntentDetailsParameters(
                    ImplicitDict.parse(
                        interaction.query.request.json,
                        PutOperationalIntentDetailsParameters,
                    )
                )
            except (ValueError, TypeError, KeyError) as e:
                check.record_failed(
                    summary=f"Failed to parse request of a 'NotifyOperationalIntentDetailsChanged' interaction with mock_uss as a PutOperationalIntentDetailsParameters",
                    details=f"{str(e)}\nRequest: {interaction.query.request.json}\n\nStack trace:\n{e.stacktrace}",
                    query_timestamps=[query.request.timestamp],
                )
                continue  # low priority failure: continue checking interactions if one cannot be parsed

        with scenario.check("Expect Notification not sent", [participant_id]) as check:
            op_intent_id = EntityID(req.operational_intent_id)
            if op_intent_id not in shared_op_intent_ids:
                check.record_failed(
                    summary=f"Observed unexpected notification for operational intent ID {req.operational_intent_id}.",
                    details=f"Notification for operational intent ID {req.operational_intent_id} triggered by subscriptions {', '.join([sub.subscription_id for sub in req.subscriptions])} with timestamp {interaction.query.request.timestamp}.",
                    query_timestamps=[query.request.timestamp],
                )


def mock_uss_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    since: StringBasedDateTime,
    *is_applicable: Callable[[Interaction], bool],
) -> Tuple[List[Interaction], Query]:
    """Retrieve mock_uss interactions given specific criteria."""

    with scenario.check(
        "Mock USS interactions logs retrievable", [mock_uss.participant_id]
    ) as check:
        try:
            interactions, query = mock_uss.get_interactions(since)
            scenario.record_query(query)
        except QueryError as e:
            for q in e.queries:
                scenario.record_query(q)
            check.record_failed(
                summary=f"Error from mock_uss when attempting to get interactions since {since}",
                details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                query_timestamps=[q.request.timestamp for q in e.queries],
            )

    return filter_interactions(interactions, is_applicable), query


def filter_interactions(
    interactions: List[Interaction], filters: Iterable[Callable[[Interaction], bool]]
) -> List[Interaction]:
    return list(filter(lambda x: all(f(x) for f in filters), interactions))


def notif_op_intent_id_filter(
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


def base_url_filter(
    base_url: str,
) -> Callable[[Interaction], bool]:
    """Returns an `is_applicable` function that detects if the request in an interaction is sent to the given base url."""

    def is_applicable(interaction: Interaction) -> bool:
        return interaction.query.request.url.startswith(base_url)

    return is_applicable


def direction_filter(
    direction: QueryDirection,
) -> Callable[[Interaction], bool]:
    """Returns an `is_applicable` filter that filters according to query direction."""

    def is_applicable(interaction: Interaction) -> bool:
        return interaction.direction == direction

    return is_applicable


def operation_filter(
    op_id: OperationID,
    **query_params: str,
) -> Callable[[Interaction], bool]:
    """
    Returns an `is_applicable` filter that filters according to operation ID.
    If the operation has query parameters, they must be provided through `**query_params`.

    Raises:
        KeyError: if query_params contains a non-existing parameter
        IndexError: if query_params is missing a parameter
    """
    op = api.OPERATIONS[op_id]
    op_path = op.path.format(**query_params)  # raises KeyError, IndexError

    def is_applicable(interaction: Interaction) -> bool:
        return interaction.query.request.method == op.verb and re.search(
            op_path, interaction.query.request.url
        )

    return is_applicable
