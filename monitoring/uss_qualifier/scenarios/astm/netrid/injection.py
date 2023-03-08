from datetime import datetime

from implicitdict import ImplicitDict

from monitoring.monitorlib.rid_automated_testing.injection_api import TestFlight


class InjectedFlight(ImplicitDict):
    uss_participant_id: str
    test_id: str
    flight: TestFlight
    query_timestamp: datetime


class InjectedTest(ImplicitDict):
    participant_id: str
    test_id: str
    version: str
