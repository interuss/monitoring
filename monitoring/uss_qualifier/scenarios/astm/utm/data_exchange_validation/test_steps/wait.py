from collections.abc import Callable
from datetime import timedelta

import arrow

from monitoring.monitorlib.clients.mock_uss.interactions import Interaction, Query
from monitoring.uss_qualifier.scenarios.scenario import TestScenario

MaxTimeToWaitForSubscriptionNotificationSeconds = 7
"""
This constant is used for waiting to check notifications for relevant operations due to subscriptions,
sent to Mock USS by another USS, or sent by Mock USS to another USS.
The details of usage of this constant are in ./validate_notification_operational_intent.md
and ./validate_no_notification_operational_intent.md
"""

WaitIntervalSeconds = 1
"""Time interval to wait between two calls to get interactions from Mock USS"""


def wait_in_intervals(
    func, scenario: TestScenario
) -> Callable[..., tuple[list[Interaction], Query]]:
    """
    This wrapper calls the given function in intervals till desired interactions (of notifications) are returned,
    or till the max wait time is reached.
    Args:
        func: Given function func must also return Tuple[List[Interaction], Query].
        scenario: Test scenario providing capability to delay.
    """

    def wrapper(*args, **kwargs) -> tuple[list[Interaction], Query]:
        wait_until = arrow.utcnow().datetime + timedelta(
            seconds=MaxTimeToWaitForSubscriptionNotificationSeconds
        )
        interactions, query = func(*args, **kwargs)
        while arrow.utcnow().datetime < wait_until:
            if interactions:
                break
            dt = (wait_until - arrow.utcnow().datetime).total_seconds()
            if dt > 0:
                scenario.sleep(
                    min(dt, WaitIntervalSeconds),
                    "the expected notification was not found yet",
                )
                interactions, query = func(*args, **kwargs)
        return interactions, query

    return wrapper
