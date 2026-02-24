import json
from datetime import timedelta

import arrow
from implicitdict import ImplicitDict, Optional
from uas_standards.astm.f3548.v21.api import OperationalIntent

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.user_interactions.notifications import UserNotification
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.clients.mock_uss.mock_uss_scd_injection_api import (
    MockUssFlightBehavior,
)
from monitoring.monitorlib.multiprocessing import SynchronizedValue

DEADLOCK_TIMEOUT = timedelta(seconds=5)
NOTIFICATIONS_LIMIT = timedelta(hours=1)
DB_CLEANUP_INTERVAL = timedelta(hours=1)
FLIGHTS_LIMIT = timedelta(hours=1)
OPERATIONAL_INTENTS_LIMIT = timedelta(hours=1)


class FlightRecord(ImplicitDict):
    """Representation of a flight in a USS"""

    flight_info: FlightInfo
    op_intent: OperationalIntent
    mod_op_sharing_behavior: Optional[MockUssFlightBehavior] = None
    locked: bool = False


class Database(ImplicitDict):
    """Simple in-memory pseudo-database tracking the state of the mock system"""

    flights: dict[str, FlightRecord | None] = {}
    cached_operations: dict[str, OperationalIntent] = {}

    flight_planning_notifications: list[UserNotification] = []
    """List of notifications sent during flight planning operations"""

    def cleanup_notifications(self):
        self.flight_planning_notifications = [
            notif
            for notif in self.flight_planning_notifications
            if notif.observed_at.datetime + NOTIFICATIONS_LIMIT
            > arrow.utcnow().datetime
        ]

    def cleanup_flights(self):
        to_cleanup = []

        for flight_id, flight in self.flights.items():
            if (
                flight
                and not flight.locked
                and flight.op_intent.reference.time_end.value.datetime + FLIGHTS_LIMIT
                < arrow.utcnow().datetime
            ):
                to_cleanup.append(flight_id)

        for flight_id in to_cleanup:
            del self.flights[flight_id]

    def cleanup_operational_intents(self):
        to_cleanup = []

        for op_id, op_intent in self.cached_operations.items():
            if (
                op_intent.reference.time_end.value.datetime + FLIGHTS_LIMIT
                < arrow.utcnow().datetime
            ):
                to_cleanup.append(op_id)

        for op_id in to_cleanup:
            del self.cached_operations[op_id]


db = SynchronizedValue[Database](
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)

TASK_DATABASE_CLEANUP = "flights database cleanup"


@webapp.periodic_task(TASK_DATABASE_CLEANUP)
def database_cleanup() -> None:
    with db.transact() as tx:
        tx.value.cleanup_notifications()
        tx.value.cleanup_flights()
        tx.value.cleanup_operational_intents()


webapp.set_task_period(TASK_DATABASE_CLEANUP, DB_CLEANUP_INTERVAL)
