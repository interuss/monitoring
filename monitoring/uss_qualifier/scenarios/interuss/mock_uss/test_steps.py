import re
from typing import Callable, Iterable, List, Tuple

from implicitdict import StringBasedDateTime
from uas_standards.astm.f3548.v21 import api
from uas_standards.astm.f3548.v21.api import EntityID, OperationID

from monitoring.monitorlib.clients.mock_uss.interactions import (
    Interaction,
    QueryDirection,
)
from monitoring.monitorlib.fetch import Query, QueryError
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSClient
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


def get_mock_uss_interactions(
    scenario: TestScenarioType,
    mock_uss: MockUSSClient,
    since: StringBasedDateTime,
    *is_applicable: Callable[[Interaction], bool],
) -> Tuple[List[Interaction], Query]:
    """Retrieves mock_uss interactions given specific criteria.
    Implements test step fragment in `get_mock_uss_interactions.md`."""

    with scenario.check(
        "Mock USS interactions logs retrievable", [mock_uss.participant_id]
    ) as check:
        try:
            interactions, query = mock_uss.get_interactions(since)
            scenario.record_query(query)
        except QueryError as e:
            scenario.record_queries(e.queries)
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


def notif_sub_id_filter(
    sub_id: EntityID,
) -> Callable[[Interaction], bool]:
    """Returns an `is_applicable` function that detects whether an op intent notification refers to the specified subscription."""

    def is_applicable(interaction: Interaction) -> bool:
        if "json" in interaction.query.request and interaction.query.request.json:
            subs = interaction.query.request.json.get("subscriptions")
            return isinstance(subs, list) and any(
                sub_id == sub.get("subscription_id") for sub in subs
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


def status_code_filter(
    status_code: int,
) -> Callable[[Interaction], bool]:
    """Returns an `is_applicable` filter that filters according to the response status code."""

    def is_applicable(interaction: Interaction) -> bool:
        return interaction.query.status_code == status_code

    return is_applicable
