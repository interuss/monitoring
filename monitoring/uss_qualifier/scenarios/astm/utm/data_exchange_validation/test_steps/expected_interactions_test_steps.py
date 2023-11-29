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
from monitoring.uss_qualifier.scenarios.scenario import (
    ScenarioCannotContinueError,
)


def expect_interuss_post_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    posted_to_url: str,
    test_step: str,
):
    scenario.begin_test_step(test_step)
    with scenario.check("Expect Notification sent") as check:
        interactions = _get_interuss_interactions_with_check(scenario, mock_uss, st)
        logger.debug(f"Checking for POST request to {posted_to_url}")
        found = any_post_interactions_to_url(interactions, posted_to_url)
        if found == False:
            check.record_failed(
                summary=f"Notification to {posted_to_url} not received",
                severity=Severity.Medium,
                details=f"Notification to {posted_to_url} not received",
                requirements="SCDxxxx",
            )
    scenario.end_test_step()


def expect_no_interuss_post_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    posted_to_url: str,
    test_step: str,
):
    scenario.begin_test_step(test_step)
    with scenario.check("Expect Notification not sent") as check:
        interactions = _get_interuss_interactions_with_check(scenario, mock_uss, st)
        logger.debug(f"Checking for POST request to {posted_to_url}")
        found = any_post_interactions_to_url(interactions, posted_to_url)
        if found == True:
            check.record_failed(
                summary=f"Notification to {posted_to_url} wrongly sent",
                severity=Severity.Medium,
                details=f"Notification to {posted_to_url} wrongly sent",
                requirements="SCDxxxx",
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
    scenario.begin_test_step(test_step)
    if mock_uss is None:
        raise ScenarioCannotContinueError("mock_uss should not be None.")

    interactions = _get_interuss_interactions_with_check(scenario, mock_uss, st)
    logger.debug(f"Checking for GET request to {get_from_url} for id {id}")
    with scenario.check("Expect GET request") as check:
        found = False
        for interaction in interactions:
            method = interaction.query.request.method
            url = interaction.query.request.url
            if method == "GET" and get_from_url in url and id in url:
                found = True
        if found == False:
            check.record_failed(
                summary=f"No GET request received at {get_from_url} for {id} ",
                severity=Severity.Medium,
                details=f"No GET request received at  {get_from_url} for {id}",
                requirements="SCDxxxx",
            )

    scenario.end_test_step()


def _get_interuss_interactions_with_check(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
) -> List[Interaction]:

    with scenario.check("MockUSS interactions request") as check:
        try:
            interactions, query = _get_interuss_interactions(mock_uss, st)
            return interactions
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
    time.sleep(5)
    if mock_uss is None:
        raise ScenarioCannotContinueError("mock_uss should not be None.")

    all_interactions, query = mock_uss.get_interactions(st)
    exclude_sub = mock_uss.session.auth_adapter.get_sub()

    def is_uss_interaction(interaction: Interaction, excl_sub: str) -> bool:
        headers = interaction.query.request.headers
        if "Authorization" in headers:
            token = headers.get("Authorization").split(" ")[1]
            payload = jwt.decode(
                token, algorithms="RS256", options={"verify_signature": False}
            )
            sub = payload["sub"]
            logger.debug(f"sub of interuss_interaction token: {sub}")
            if sub == excl_sub:
                logger.debug(f"Excluding interaction with sub: {sub} ")
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
    test_step: str,
):
    scenario.begin_test_step(test_step)
    interactions, _ = _get_interuss_interactions(mock_uss, st)
    logger.debug(f"Checking for POST request to {posted_to_url}")
    found = any_post_interactions_to_url(interactions, posted_to_url)
    if found:
        msg = f"As a precondition for the scenario tests, there should have been no post made to {posted_to_url}"
        raise ScenarioCannotContinueError(msg)

    scenario.end_test_step()


def any_post_interactions_to_url(
    interactions: List[Interaction], posted_to_url: str
) -> bool:
    found = False
    for interaction in interactions:
        method = interaction.query.request.method
        url = interaction.query.request.url
        if method == "POST" and posted_to_url in url:
            found = True
    return found
