import json
from datetime import timedelta

from implicitdict import ImplicitDict, Optional
from uas_standards.astm.f3548.v21.api import EntityID, OperationalIntent

from monitoring.mock_uss.user_interactions.notifications import UserNotification
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.clients.mock_uss.mock_uss_scd_injection_api import (
    MockUssFlightBehavior,
)
from monitoring.monitorlib.multiprocessing import SynchronizedValue

DEADLOCK_TIMEOUT = timedelta(seconds=5)


class MockUSSFlightID(str):
    """The identity of a flight, as tracked/managed by mock_uss"""

    pass


class FlightRecord(ImplicitDict):
    """Representation of a flight in a USS"""

    flight_info: FlightInfo
    op_intent: OperationalIntent
    mod_op_sharing_behavior: Optional[MockUssFlightBehavior] = None
    locked: bool = False


class Database(ImplicitDict):
    """Simple in-memory pseudo-database tracking the state of the mock system"""

    flights: dict[MockUSSFlightID, FlightRecord | None] = {}
    """Collection of flights managed by mock_uss, referenced by flight ID.
    
    When the value is None, this indicates that the flight of the specified ID is currently in the process of being
    created and should be treated as locked."""

    cached_operations: dict[EntityID, OperationalIntent] = {}

    flight_planning_notifications: list[UserNotification] = []
    """List of notifications sent during flight planning operations"""


db = SynchronizedValue[Database](
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
