import json
from datetime import timedelta

from implicitdict import ImplicitDict, Optional
from uas_standards.astm.f3548.v21.api import OperationalIntent

from monitoring.mock_uss.user_interactions.notifications import UserNotification
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.clients.mock_uss.mock_uss_scd_injection_api import (
    MockUssFlightBehavior,
)
from monitoring.monitorlib.multiprocessing import SynchronizedValue

DEADLOCK_TIMEOUT = timedelta(seconds=5)


class FlightRecord(ImplicitDict):
    """Representation of a flight in mock_uss"""

    # TODO(mock_uss_flight_id): Add flight ID that is independent of op_intent
    flight_info: FlightInfo
    op_intent: Optional[OperationalIntent] = None
    mod_op_sharing_behavior: Optional[MockUssFlightBehavior] = None
    locked: bool = False


class Database(ImplicitDict):
    """Simple in-memory pseudo-database tracking the state of the mock system"""

    flights: dict[str, FlightRecord | None] = {}
    cached_operations: dict[str, OperationalIntent] = {}

    flight_planning_notifications: list[UserNotification] = []
    """List of notifications sent during flight planning operations"""


db = SynchronizedValue[Database](
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
