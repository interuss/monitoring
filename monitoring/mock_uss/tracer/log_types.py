from __future__ import annotations

from abc import abstractmethod
import sys
from typing import Optional, Type

from implicitdict import ImplicitDict, StringBasedDateTime
from monitoring.monitorlib.fetch import rid as rid_fetch, RequestDescription, summarize
from monitoring.monitorlib.fetch import scd as scd_fetch
from monitoring.monitorlib.fetch.rid import FetchedISAs
from monitoring.monitorlib.mutate import rid as rid_mutate
from monitoring.monitorlib.mutate import scd as scd_mutate


class TracerLogEntry(ImplicitDict):
    """A log entry for a tracer event.

    All subclasses must be defined in this module.
    """

    object_type: str
    """The type of log entry that this is (automatically populated according to concrete log entry class name."""

    def __init__(self, *args, **kwargs):
        kwargs = kwargs.copy()
        kwargs["object_type"] = type(self).__name__
        super(TracerLogEntry, self).__init__(*args, **kwargs)

    @staticmethod
    @abstractmethod
    def prefix_code() -> str:
        raise NotImplementedError()

    def human_info(self) -> dict:
        """Reorganize the information in this log entry into human-consumable form.

        This form will be displayed to tracer viewers when viewing the log in a browser.
        """
        return self

    @staticmethod
    def entry_type(type_name: Optional[str]) -> Optional[Type]:
        matches = [
            cls
            for name, cls in sys.modules[__name__].__dict__.items()
            if name == type_name
            and isinstance(cls, type)
            and issubclass(cls, TracerLogEntry)
        ]
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(
                f"Multiple TracerLogEntry classes named `{type_name}` found"
            )
        return matches[0]

    @staticmethod
    def entry_type_from_prefix(prefix_code: str) -> Optional[Type[TracerLogEntry]]:
        matches = [
            cls
            for name, cls in sys.modules[__name__].__dict__.items()
            if isinstance(cls, type)
            and issubclass(cls, TracerLogEntry)
            and not cls is TracerLogEntry
            and cls.prefix_code() == prefix_code
        ]
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(
                f"Multiple TracerLogEntry classes with prefix code `{prefix_code}` found"
            )
        return matches[0]


class PollStart(TracerLogEntry):
    """Log entry for when polling starts."""

    @staticmethod
    def prefix_code() -> str:
        return "poll_start"

    config: dict
    """Configuration used for polling."""


class RIDSubscribe(TracerLogEntry):
    """Log entry for establishing an RID subscription."""

    @staticmethod
    def prefix_code() -> str:
        return "rid_subscribe"

    changed_subscription: rid_mutate.ChangedSubscription
    """Subscription, as created in the DSS."""


class RIDISANotification(TracerLogEntry):
    """Log entry for an incoming RID ISA notification from another USS."""

    @staticmethod
    def prefix_code() -> str:
        return "notify_isa"

    observation_area_id: str
    """ID of observation area with which this notification is associated."""

    request: RequestDescription
    """Incoming notification request from other USS."""


class RIDUnsubscribe(TracerLogEntry):
    """Log entry for the removal of an RID subscription."""

    @staticmethod
    def prefix_code() -> str:
        return "rid_unsubscribe"

    existing_subscription: rid_fetch.FetchedSubscription
    """Subscription, as read from the DSS just before deletion."""

    deleted_subscription: Optional[rid_mutate.ChangedSubscription]
    """Subscription returned from DSS upon deletion."""


class PollISAs(TracerLogEntry):
    """Log entry for polling identification service areas from the DSS."""

    @staticmethod
    def prefix_code() -> str:
        return "poll_isas"

    poll: FetchedISAs
    """Result of polling ISAs."""

    def human_info(self) -> dict:
        return {
            "summary": summarize.isas(self.poll),
            "details": self,
        }


class PollFlights(TracerLogEntry):
    """Log entry for client-requested poll of all RID flights in an area."""

    @staticmethod
    def prefix_code() -> str:
        return "clientrequest_pollflights"

    observation_area_id: str
    """ID of the observation area for which the flight polling was requested."""

    poll: rid_fetch.FetchedFlights
    """All information relating to the RID flights fetched."""

    def human_info(self) -> dict:
        return {
            "summary": summarize.flights(self.poll),
            "details": self,
        }


class SCDSubscribe(TracerLogEntry):
    """Log entry for establishing an SCD subscription."""

    @staticmethod
    def prefix_code() -> str:
        return "scd_subscribe"

    changed_subscription: scd_mutate.MutatedSubscription
    """Subscription, as created in the DSS."""


class OperationalIntentNotification(TracerLogEntry):
    """Log entry for an incoming operational intent notification from another USS."""

    @staticmethod
    def prefix_code() -> str:
        return "notify_op"

    observation_area_id: str
    """ID of observation area with which this notification is associated."""

    request: RequestDescription
    """Incoming notification request from other USS."""


class ConstraintNotification(TracerLogEntry):
    """Log entry for an incoming constraint notification from another USS."""

    @staticmethod
    def prefix_code() -> str:
        return "notify_constraint"

    observation_area_id: str
    """ID of observation area with which this notification is associated."""

    request: RequestDescription
    """Incoming notification request from other USS."""


class SCDUnsubscribe(TracerLogEntry):
    """Log entry for the removal of an SCD subscription."""

    @staticmethod
    def prefix_code() -> str:
        return "scd_unsubscribe"

    existing_subscription: scd_fetch.FetchedSubscription
    """Subscription, as read from the DSS just before deletion."""

    deleted_subscription: Optional[scd_mutate.MutatedSubscription]
    """Subscription returned from DSS upon deletion."""


class PollOperationalIntents(TracerLogEntry):
    """Log entry for polling operational intents from DSS and managing USSs."""

    @staticmethod
    def prefix_code() -> str:
        return "poll_ops"

    poll: scd_fetch.FetchedEntities
    """Results from polling operational intents from DSS and managing USSs."""

    def human_info(self) -> dict:
        return {
            "summary": summarize.entities(self.poll),
            "details": self,
        }


class PollConstraints(TracerLogEntry):
    """Log entry for polling constraints from DSS and managing USSs."""

    @staticmethod
    def prefix_code() -> str:
        return "poll_constraints"

    poll: scd_fetch.FetchedEntities
    """Results from polling constraints from DSS and managing USSs."""

    def human_info(self) -> dict:
        return {
            "summary": summarize.entities(self.poll),
            "details": self,
        }


class BadRoute(TracerLogEntry):
    """Log entry for access to an undefined (bad) endpoint."""

    @staticmethod
    def prefix_code() -> str:
        return "uss_badroute"

    request: RequestDescription
    """Incoming notification request from other USS."""


class ObservationAreaImportError(TracerLogEntry):
    """Log entry for an error while attempting to import an operation area from subscriptions in the DSS."""

    @staticmethod
    def prefix_code() -> str:
        return "import_obs_areas_error"

    rid_subscriptions: Optional[rid_fetch.FetchedSubscriptions]
    """Result of attempting to fetch RID subscriptions"""


class TracerShutdown(TracerLogEntry):
    """Log entry for when tracer shuts down."""

    @staticmethod
    def prefix_code() -> str:
        return "tracer_stop"

    timestamp: StringBasedDateTime
