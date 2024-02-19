import arrow
from monitoring.monitorlib.delay import sleep
from datetime import timedelta
from monitoring.monitorlib.clients.mock_uss.interactions import (
    Interaction,
    Query,
)
from typing import List, Tuple
from loguru import logger

MaxTimeToWaitForSubscriptionNotificationSeconds = 7
"""
This constant is used for waiting to check notifications for relevant operations due to subscriptions,
sent to Mock USS by another USS, or sent by Mock USS to another USS.
The details of usage of this constant are in ./validate_notification_operational_intent.md
and ./validate_no_notification_operational_intent.md
"""

WaitIntervalSeconds = 1
"""Time interval to wait between two calls to get interactions from Mock USS"""


def wait_in_intervals(func):
    # Returns a function that returns a Tuple[List[Interaction], Query].
    # Given function func must also return Tuple[List[Interaction], Query].
    # This wrapper calls the given function in intervals till desired interactions (of notifications) are returned,
    # or till the max wait time is reached.

    def wrapper(*args, **kwargs) -> Tuple[List[Interaction], Query]:
        wait_until = arrow.utcnow().datetime + timedelta(
            seconds=MaxTimeToWaitForSubscriptionNotificationSeconds
        )
        while arrow.utcnow().datetime < wait_until:
            interactions, query = func(*args, **kwargs)
            if interactions:
                break
            dt = (wait_until - arrow.utcnow().datetime).total_seconds()
            if dt > 0:
                sleep(
                    min(dt, WaitIntervalSeconds),
                    "the expected notification was not found yet",
                )
        return interactions, query

    return wrapper
