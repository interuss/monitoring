from enum import StrEnum


class NotificationIndexImplementation(StrEnum):
    ZeroBasedIncrementPerDispatch = "ZeroBasedIncrementPerDispatch"
    """Notification index starts at 0 and is incremented by 1 each time a notification is requested/sent due to the associated subscription."""

    TimedBased = "TimeBased"
    """Notification index is populated based on the clock of the DSS instance serving the request."""
