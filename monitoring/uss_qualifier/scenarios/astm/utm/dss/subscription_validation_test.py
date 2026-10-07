from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from implicitdict import StringBasedDateTime

from monitoring.monitorlib.fetch import RequestDescription, ResponseDescription
from monitoring.monitorlib.fetch.scd import FetchedSubscription
from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.sub.crud import (
    sub_get_query,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.subscription_validation import (
    SubscriptionValidation,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    PendingCheck,
    ScenarioCannotContinueError,
)


@pytest.mark.parametrize(
    "duration,has_subscription,should_fail,should_delete",
    [
        (timedelta(hours=24), True, False, False),
        (timedelta(hours=24, minutes=10), True, True, True),
        (timedelta(hours=23), True, True, True),
        (None, True, True, True),
        (None, False, True, False),
    ],
)
# This test is AI-generated and has not been closely inspected by a human.
def test_truncated_subscription_response(
    duration: timedelta | None,
    has_subscription: bool,
    should_fail: bool,
    should_delete: bool,
):
    now = datetime(2026, 10, 7, tzinfo=UTC)
    response_json = {}
    if has_subscription:
        subscription = {
            "id": "subscription-id",
            "version": "version-1",
            "notification_index": 0,
            "uss_base_url": "https://uss.example",
        }
        if duration is not None:
            subscription["time_start"] = {
                "format": "RFC3339",
                "value": StringBasedDateTime(now),
            }
            subscription["time_end"] = {
                "format": "RFC3339",
                "value": StringBasedDateTime(now + duration),
            }
        response_json["subscription"] = subscription
    changed = MutatedSubscription(
        request=RequestDescription(
            method="PUT",
            url="https://dss.example/subscriptions/subscription-id",
            initiated_at=StringBasedDateTime(now),
        ),
        response=ResponseDescription(
            code=200,
            json=response_json,
            reported=StringBasedDateTime(now),
            elapsed_s=0,
        ),
    )
    scenario = MagicMock(spec=SubscriptionValidation)
    scenario._sub_id = "subscription-id"
    scenario._dss = MagicMock(participant_id="dss")
    check = MagicMock(spec=PendingCheck)

    SubscriptionValidation._check_properly_truncated(scenario, check, changed)

    assert check.record_failed.called == should_fail
    if should_fail:
        assert check.record_failed.call_args.kwargs["query_timestamps"] == [now]
    assert scenario._dss.delete_subscription.called == should_delete
    if should_delete:
        scenario._dss.delete_subscription.assert_called_once_with(
            sub_id="subscription-id", sub_version="version-1"
        )


@pytest.mark.parametrize(
    "status_code,valid_subscription", [(200, True), (200, False), (404, False)]
)
# This test is AI-generated and has not been closely inspected by a human.
def test_get_subscription_preserves_query_or_stops(
    status_code: int, valid_subscription: bool
):
    now = datetime(2026, 10, 7, tzinfo=UTC)
    response_json = {}
    if valid_subscription:
        response_json["subscription"] = {
            "id": "subscription-id",
            "version": "version-1",
            "notification_index": 0,
            "uss_base_url": "https://uss.example",
        }
    fetched = FetchedSubscription(
        request=RequestDescription(
            method="GET",
            url="https://dss.example/subscriptions/subscription-id",
            initiated_at=StringBasedDateTime(now),
        ),
        response=ResponseDescription(
            code=status_code,
            json=response_json,
            reported=StringBasedDateTime(now),
            elapsed_s=0,
        ),
    )
    scenario = MagicMock()
    dss = MagicMock(participant_id="dss")
    dss.get_subscription.return_value = fetched

    if valid_subscription:
        subscription, query = sub_get_query(scenario, dss, "subscription-id")
        assert subscription.id == "subscription-id"
        assert query is fetched
    else:
        with pytest.raises(ScenarioCannotContinueError):
            sub_get_query(scenario, dss, "subscription-id")
        check = scenario.check.return_value.__enter__.return_value
        assert check.record_failed.call_args.kwargs["query_timestamps"] == [now]

    scenario.record_query.assert_called_once_with(fetched)
