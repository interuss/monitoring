import json
from datetime import timedelta

import arrow
from implicitdict import ImplicitDict, Optional

from monitoring.mock_uss.app import webapp
from monitoring.monitorlib.multiprocessing import SynchronizedValue
from monitoring.monitorlib.rid_automated_testing import injection_api

from .behavior import ServiceProviderBehavior
from .user_notifications import ServiceProviderUserNotifications

DB_CLEANUP_INTERVAL = timedelta(hours=1)
"""Clean database this often."""

FLIGHTS_LIMIT = timedelta(hours=1)
"""Automatically remove flights we manage after this long beyond their end time."""

NOTIFICATIONS_LIMIT = timedelta(hours=1)
"""Automatically remove notifications after this long beyond their observation time."""


class TestRecord(ImplicitDict):
    """Representation of RID SP's record of a set of injected test flights"""

    version: str
    flights: list[injection_api.TestFlight]
    isa_version: Optional[str] = None

    def __init__(self, **kwargs):
        kwargs["flights"] = [
            injection_api.TestFlight(**flight) for flight in kwargs["flights"]
        ]
        for flight in kwargs["flights"]:
            flight.order_telemetry()

        super().__init__(**kwargs)

    def cleanup_flights(self):
        self.flights = [
            flight
            for flight in self.flights
            if flight.get_span()[1]
            and flight.get_span()[1] + FLIGHTS_LIMIT > arrow.utcnow().datetime  # pyright: ignore[reportOptionalOperand]
        ]


class Database(ImplicitDict):
    """Simple pseudo-database structure tracking the state of the mock system"""

    tests: dict[str, TestRecord] = {}
    behavior: ServiceProviderBehavior = ServiceProviderBehavior()
    notifications: ServiceProviderUserNotifications = ServiceProviderUserNotifications()

    def cleanup_notifications(self):
        self.notifications.cleanup(NOTIFICATIONS_LIMIT)

    def cleanup_flights(self):
        to_cleanup = []

        for test_id, test in self.tests.items():
            if test.flights:
                test.cleanup_flights()

                if not test.flights:
                    to_cleanup.append(test_id)

        for test_id in to_cleanup:
            del self.tests[test_id]


db = SynchronizedValue[Database](
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)

TASK_DATABASE_CLEANUP = "ridsp database cleanup"


@webapp.periodic_task(TASK_DATABASE_CLEANUP)
def database_cleanup() -> None:
    with db.transact() as tx:
        tx.value.cleanup_notifications()
        tx.value.cleanup_flights()


webapp.set_task_period(TASK_DATABASE_CLEANUP, DB_CLEANUP_INTERVAL)
