from __future__ import annotations

from typing import List, Tuple
import time
import jwt

from monitoring.monitorlib.fetch import QueryError, Query
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from implicitdict import StringBasedDateTime
from loguru import logger
from monitoring.monitorlib.clients.mock_uss.interactions import Interaction


def expect_interuss_post_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    posted_to_url: str,
    test_step: str,
):
    """
    This step checks if a notification was sent to a subscribed USS, from time 'st' to now
    Args:
        scenario:
        mock_uss:
        st:
        posted_to_url: url of the subscribed USS
        test_step:

    Returns:

    """
    scenario.begin_test_step(test_step)
    interactions, query = _get_interuss_interactions_with_check(scenario, mock_uss, st)
    logger.debug(f"Checking for POST request to {posted_to_url}")
    found = any_post_interactions_to_url(interactions, posted_to_url)
    with scenario.check("Expect Notification sent") as check:
        if not found:
            check.record_failed(
                summary=f"Notification to {posted_to_url} not sent",
                severity=Severity.Medium,
                details=f"Notification to {posted_to_url} not sent",
                requirements="SCD0085",
                query_timestamps=[query.request.timestamp],
            )
    scenario.end_test_step()


def expect_no_interuss_post_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    posted_to_url: str,
    test_step: str,
):
    """
    This step checks no notification was sent to any USS as no DSS entity was created, from time 'st' to now
    Args:
        scenario:
        mock_uss:
        st:
        posted_to_url:
        test_step:

    Returns:

    """
    scenario.begin_test_step(test_step)
    interactions, query = _get_interuss_interactions_with_check(scenario, mock_uss, st)
    logger.debug(f"Checking for POST request to {posted_to_url}")
    found = any_post_interactions_to_url(interactions, posted_to_url)
    with scenario.check("Expect Notification not sent") as check:
        if found:
            check.record_failed(
                summary=f"Notification to {posted_to_url} wrongly sent for an entity not created.",
                severity=Severity.Medium,
                details=f"Notification to {posted_to_url} wrongly sent for an entity not created.",
                requirements="interuss.f3548.notification_requirements.NoDssEntityNoNotification",
                query_timestamps=[query.request.timestamp],
            )
    scenario.end_test_step()


def expect_interuss_get_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    get_from_url: str,
    id: str,
    test_step: str,
):
    """
    This step checks a GET request to a USS was made for an existing entity, from time 'st' to now
    Args:
        scenario:
        mock_uss:
        st:
        get_from_url: USS managing the entity
        id: entity id
        test_step:

    Returns:

    """
    scenario.begin_test_step(test_step)
    interactions, query = _get_interuss_interactions_with_check(scenario, mock_uss, st)
    logger.debug(f"Checking for GET request to {get_from_url} for id {id}")
    found = False
    for interaction in interactions:
        method = interaction.query.request.method
        url = interaction.query.request.url
        if method == "GET" and url.startswith(get_from_url) and id in url:
            found = True
    with scenario.check("Expect GET request") as check:
        if not found:
            check.record_failed(
                summary=f"No GET request received at {get_from_url} for {id} ",
                severity=Severity.Medium,
                details=f"No GET request received at  {get_from_url} for {id}",
                requirements="SCD0035",
                query_timestamps=[query.request.timestamp],
            )
    scenario.end_test_step()


def _get_interuss_interactions_with_check(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
) -> Tuple[List[Interaction], Query]:
    """
    Method to get interuss interactions with a scenario check from mock_uss from time 'st' to now.
    Args:
        scenario:
        mock_uss:
        st:

    Returns:

    """
    with scenario.check("MockUSS interactions request") as check:
        try:
            interactions, query = _get_interuss_interactions(mock_uss, st)
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
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
) -> Tuple[List[Interaction], Query]:
    """
        Method to get interuss interactions from mock_uss from time 'st' to now.
    Args:
        mock_uss:
        st:

    Returns:

    """
    # Wait - To make sure that interuss interactions are received and recorded
    # Using a guess value of 5 seconds
    time.sleep(5)

    all_interactions, query = mock_uss.get_interactions(st)
    exclude_sub = mock_uss.session.auth_adapter.get_sub()

    def get_client_sub(headers):
        token = headers.get("Authorization").split(" ")[1]
        payload = jwt.decode(
            token, algorithms="RS256", options={"verify_signature": False}
        )
        return payload["sub"]

    def is_uss_interaction(interaction: Interaction, excl_sub: str) -> bool:
        headers = interaction.query.request.headers
        if "Authorization" in headers:
            sub = get_client_sub(headers)
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
    posted_to_url: str,
) -> bool:
    interactions, query = _get_interuss_interactions(mock_uss, st)
    scenario.record_query(query)
    return any_post_interactions_to_url(interactions, posted_to_url)


def any_post_interactions_to_url(
    interactions: List[Interaction], posted_to_url: str
) -> bool:
    found = False
    for interaction in interactions:
        method = interaction.query.request.method
        url = interaction.query.request.url
        if method == "POST" and url.startswith(posted_to_url):
            return True
    return found
