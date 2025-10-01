import json
from datetime import timedelta

from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21.api import OperationalIntent

from monitoring.mock_uss.user_interactions.notifications import UserNotification
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.clients.mock_uss.mock_uss_scd_injection_api import (
    MockUssFlightBehavior,
)
from monitoring.monitorlib.multiprocessing import SynchronizedValue

DEADLOCK_TIMEOUT = timedelta(seconds=5)


class FlightRecord(ImplicitDict):
    """Representation of a flight in a USS"""

    flight_info: FlightInfo
    op_intent: OperationalIntent
    mod_op_sharing_behavior: MockUssFlightBehavior | None = None
    locked: bool = False


class Database(ImplicitDict):
    """Simple in-memory pseudo-database tracking the state of the mock system"""

    flights: dict[str, FlightRecord | None] = {}
    cached_operations: dict[str, OperationalIntent] = {}

    flight_planning_notifications: list[UserNotification] = []
    """List of notifications sent during flight planning operations"""


db = SynchronizedValue(
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
