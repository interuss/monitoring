from __future__ import annotations

from typing import List, Optional
import time
import jwt

from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from implicitdict import StringBasedDateTime
from loguru import logger
from monitoring.mock_uss.interaction_logging.interactions import Interaction

def expect_interuss_post_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    posted_to_url: str,
    test_step: str,
):
    found = False
    if mock_uss is not None:
        interactions = _get_interuss_interactions(scenario, mock_uss, st, test_step)
        logger.debug(f"Checking for Post to {posted_to_url}")
        with scenario.check("Expect Notification sent" ) as check:
            found = False
            for interaction in interactions:
                method = interaction.query.request.method
                url = interaction.query.request.url
                if method == "POST" and posted_to_url in url:
                    found = True
            if found == False:
                check.record_failed(
                    summary=f"Notification to {posted_to_url} not received",
                    severity=Severity.Medium,
                    details=f"Notification to {posted_to_url} not received",
                    requirements="SCDxxxx"
                )
        scenario.end_test_step()

    return found

def expect_no_interuss_post_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    posted_to_url: str,
    test_step: str,
):
    found = False
    if mock_uss is not None:
        interactions = _get_interuss_interactions(scenario, mock_uss, st, test_step)
        logger.debug(f"Checking for Post to {posted_to_url}")
        with scenario.check("Expect Notification not sent" ) as check:
            found = False
            for interaction in interactions:
                method = interaction.query.request.method
                url = interaction.query.request.url
                if method == "POST" and posted_to_url in url:
                    found = True
            if found == True:
                check.record_failed(
                    summary=f"Notification to {posted_to_url} wrongly sent",
                    severity=Severity.Medium,
                    details=f"Notification to {posted_to_url} wrongly sent",
                    requirements="SCDxxxx"
                )
        scenario.end_test_step()

    return found

def expect_interuss_get_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    get_from_url: str,
    id: str,
    test_step: str,
):
    found = False
    if mock_uss is not None:
        interactions = _get_interuss_interactions(scenario, mock_uss, st, test_step)
        logger.debug(f"Checking for Get to {get_from_url} for id {id}")
        with scenario.check("Expect GET interaction" ) as check:
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
                    requirements="SCDxxxx"
                )

        scenario.end_test_step()
    return found

def _get_interuss_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    st: StringBasedDateTime,
    test_step: str,
) -> List[Interaction]:
    scenario.begin_test_step(test_step)
    time.sleep(5)
    all_interactions = mock_uss.get_interactions(st)
    exclude_sub = mock_uss.session.auth_adapter.get_sub()

    def is_uss_interaction(interaction: Interaction, excl_sub: str) -> bool:
        headers = interaction.query.request.headers
        if "Authorization" in headers:
            token = headers.get("Authorization").split(" ")[1]
            payload = jwt.decode(token, algorithms="RS256", options={"verify_signature": False})
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

    scenario.record_interuss_interactions(interuss_interactions)

    return interuss_interactions
