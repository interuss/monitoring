import json
from typing import Dict, Optional

from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.multiprocessing import SynchronizedValue
from uas_standards.interuss.automated_testing.scd.v1 import api as scd_injection_api
from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentReference,
    OperationalIntent,
    OperationalIntentDetails,
)
from monitoring.monitorlib.mock_uss_interface.mock_uss_scd_injection_api import (
    MockUssFlightBehavior,
)


class FlightRecord(ImplicitDict):
    """Representation of a flight in a USS"""

    flight_info: FlightInfo
    op_intent: OperationalIntent
    mod_op_sharing_behavior: Optional[MockUssFlightBehavior]
    locked: bool = False


class Database(ImplicitDict):
    """Simple in-memory pseudo-database tracking the state of the mock system"""

    flights: Dict[str, Optional[FlightRecord]] = {}
    cached_operations: Dict[str, OperationalIntent] = {}


db = SynchronizedValue(
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
