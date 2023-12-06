from __future__ import annotations

import datetime
from typing import List, Tuple, Optional
import time
import jwt

from monitoring.monitorlib.fetch import QueryError, Query
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from implicitdict import StringBasedDateTime
from loguru import logger
from monitoring.monitorlib.clients.mock_uss.interactions import Interaction
from monitoring.uss_qualifier.scenarios.astm.utm.data_exchange_validation.test_steps.constants import (
    MaxTimeToWaitForSubscriptionNotificationSeconds as max_wait_time,
)


def expect_interuss_post_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    posted_to_url: str,
    participant_id: str,
    plan_request_time: datetime.datetime,
    test_step: str,
):
    """
    This step checks if a notification was sent to a subscribed USS, from time 'st' to now
    Args:
        posted_to_url: url of the subscribed USS
        participant_id: id of the participant responsible to send the notification
        plan_request_time: timestamp of the flight plan query that would lead to sending notification
    Returns:

    """
    scenario.begin_test_step(test_step)
    time_waited = 0
    while time_waited <= max_wait_time:
        duration = (
            1 if max_wait_time - time_waited >= 1 else (max_wait_time - time_waited)
        )
        interactions, query = _get_interuss_interactions_with_check(
            scenario,
            mock_uss,
            st,
            duration,
        )
        found = any_post_interactions_to_url(interactions, posted_to_url)
        time_waited += duration
        if found:
            logger.debug(f"Waited for {time_waited} to check notifications.")
            break

    with scenario.check("Expect Notification sent", participant_id) as check:
        if not found:
            check.record_failed(
                summary=f"Notification to {posted_to_url} not sent",
                severity=Severity.Medium,
                details=f"Notification to {posted_to_url} not sent even though DSS instructed the planning USS to notify due to subscription.",
                query_timestamps=[plan_request_time, query.request.timestamp],
            )
    scenario.end_test_step()


def expect_no_interuss_post_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    participant_id: str,
    test_step: str,
):
    """
    This step checks no notification was sent to any USS as no DSS entity was created, from time 'st' to now
    Args:
        participant_id: id of the participant responsible to send the notification
    """
    scenario.begin_test_step(test_step)
    # Get interuss interactions in the next MaxTimeToWaitForSubscriptionNotificationSeconds duration
    interactions, query = _get_interuss_interactions_with_check(
        scenario,
        mock_uss,
        st,
        max_wait_time,
    )
    found = any_post_interactions_to_url(interactions)
    with scenario.check("Expect Notification not sent", participant_id) as check:
        if found:
            check.record_failed(
                summary=f"Notification was wrongly sent for an entity not created.",
                severity=Severity.Medium,
                details=f"Notification was wrongly sent for an entity not created.",
                query_timestamps=[query.request.timestamp],
            )
    scenario.end_test_step()


def expect_get_requests_to_mock_uss(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    mock_uss_base_url: str,
    id: str,
    participant_id: str,
    test_step: str,
):
    """
    This step checks a GET request to a USS was made for an existing entity, from time 'st' to now
    Args:
        mock_uss_base_url: url of the mock_uss that is managing the entity
        id: entity id
        participant_id: id of the participant responsible to send GET request

    Returns:

    """
    scenario.begin_test_step(test_step)
    interactions, query = _get_interuss_interactions_with_check(scenario, mock_uss, st)
    logger.debug(f"Checking for GET request to {mock_uss_base_url} for id {id}")
    found = False
    for interaction in interactions:
        method = interaction.query.request.method
        url = interaction.query.request.url
        if method == "GET" and url.startswith(mock_uss_base_url) and id in url:
            found = True
            break
    with scenario.check("Expect GET request", participant_id) as check:
        if not found:
            check.record_failed(
                summary=f"No GET request received at {mock_uss_base_url} for {id} ",
                severity=Severity.Medium,
                details=f"No GET request received at  {mock_uss_base_url} for {id}. A planning USS in the area should have sent a reques to get the intent details.",
                query_timestamps=[query.request.timestamp],
            )
    scenario.end_test_step()


def _get_interuss_interactions_with_check(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    wait_time_sec: Optional[int] = 0,
) -> Tuple[List[Interaction], Query]:
    """
    Method to get interuss interactions with a scenario check from mock_uss from time 'st' to now.
    Args:
        wait_time_sec: Seconds to wait for getting interactions like asynchronous notifications
    """
    with scenario.check(
        "MockUSS interactions request", mock_uss.participant_id
    ) as check:
        try:
            interactions, query = _get_interuss_interactions(
                mock_uss, st, wait_time_sec
            )
            scenario.record_query(query)
            return interactions, query
        except QueryError as e:
            for q in e.queries:
                scenario.record_query(q)
            check.record_failed(
                summary=f"Error from mock_uss when attempting to get interactions from_time {st}",
                severity=Severity.High,
                details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
                query_timestamps=[q.request.timestamp for q in e.queries],
            )


def _get_interuss_interactions(
    mock_uss: MockUSSClient, st: StringBasedDateTime, wait_time: Optional[int] = 0
) -> Tuple[List[Interaction], Query]:
    """
        Method to get interuss interactions from mock_uss from time 'st' to now.
    Args:
        wait_time: Seconds to wait for getting interactions like asynchronous notifications.

    """
    time.sleep(wait_time)

    all_interactions, query = mock_uss.get_interactions(st)
    exclude_sub = mock_uss.session.auth_adapter.get_sub()

    def get_client_sub(query: Query):
        headers = query.request.headers
        if "Authorization" in headers:
            token = headers.get("Authorization").split(" ")[1]
            payload = jwt.decode(
                token, algorithms="RS256", options={"verify_signature": False}
            )
            return payload["sub"]

    def is_uss_interaction(interaction: Interaction, excl_sub: str) -> bool:
        sub = get_client_sub(interaction.query)
        if sub:
            if sub == excl_sub:
                return False
            else:
                return True
        else:
            logger.error(f"Interaction received without Authorization : {interaction}")
            return False

    interuss_interactions = []
    for interaction in all_interactions:
        if is_uss_interaction(interaction, exclude_sub):
            interuss_interactions.append(interaction)
            logger.debug(
                f"Interuss interaction reported : {interaction.query.request.method} {interaction.query.request.url} "
                f"with response {interaction.query.response.status_code}"
            )

    return interuss_interactions, query


def precondition_no_post_interaction(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
) -> bool:
    """
    This method helps check a precondition that no POST is sent by mock_uss to a USS, as no subscription exists.
    """
    interactions, query = _get_interuss_interactions(
        mock_uss,
        st,
    )
    scenario.record_query(query)
    return any_post_interactions_to_url(interactions)


def any_post_interactions_to_url(
    interactions: List[Interaction], posted_to_url: Optional[str] = None
) -> bool:
    """
    Checks if there is any POST request made to 'posted_to_url', and returns True if found.
    If 'posted_to_url' is None, any POST request found returns True.
    """
    for interaction in interactions:
        method = interaction.query.request.method
        url = interaction.query.request.url
        if method == "POST":
            if posted_to_url is None or url.startswith(posted_to_url):
                return True
    return False
