from enum import StrEnum


class SubscriptionCreationMode(StrEnum):
    GetDeleteCreate = "GetDeleteCreate"
    """First, attempt to get an existing subscription with this ID.  If the subscription exists, delete it and any operational intents that depend on it.  Then, create the new subscription as specified."""


class SubscriptionDeletionMode(StrEnum):
    GetDeleteIfExist = "GetDeleteIfExist"
    """First, attempt to get an existing subscription with this ID.  If the subscription exists, delete it and any operational intents that depend on it.  If the subscription doesn't exist, do nothing."""
