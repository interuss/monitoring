import json
from datetime import timedelta
from typing import Dict, Optional

from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.multiprocessing import SynchronizedValue
from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21.api import (
    OperationalIntent,
)
from monitoring.monitorlib.clients.mock_uss.mock_uss_scd_injection_api import (
    MockUssFlightBehavior,
)

DEADLOCK_TIMEOUT = timedelta(seconds=5)


class FlightRecord(ImplicitDict):
    """Representation of a flight in a USS"""

    flight_info: FlightInfo
    op_intent: OperationalIntent
    mod_op_sharing_behavior: Optional[MockUssFlightBehavior] = None
    locked: bool = False


class Database(ImplicitDict):
    """Simple in-memory pseudo-database tracking the state of the mock system"""

    flights: Dict[str, Optional[FlightRecord]] = {}
    cached_operations: Dict[str, OperationalIntent] = {}


db = SynchronizedValue(
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
