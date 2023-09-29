import json
from typing import Dict, Optional

from monitoring.monitorlib.multiprocessing import SynchronizedValue
from monitoring.monitorlib.scd_automated_testing import scd_injection_api
from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentReference,
    OperationalIntent,
)


class FlightRecord(ImplicitDict):
    """Representation of a flight in a USS"""

    op_intent_injection: scd_injection_api.OperationalIntentTestInjection
    flight_authorisation: scd_injection_api.FlightAuthorisationData
    op_intent_reference: OperationalIntentReference
    locked: bool = False


class Database(ImplicitDict):
    """Simple in-memory pseudo-database tracking the state of the mock system"""

    flights: Dict[str, Optional[FlightRecord]] = {}
    cached_operations: Dict[str, OperationalIntent] = {}


db = SynchronizedValue(
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
