import json

from implicitdict import ImplicitDict

from monitoring.monitorlib.multiprocessing import SynchronizedValue
from monitoring.monitorlib.rid_automated_testing import injection_api

from .behavior import ServiceProviderBehavior
from .user_notifications import ServiceProviderUserNotifications


class TestRecord(ImplicitDict):
    """Representation of RID SP's record of a set of injected test flights"""

    version: str
    flights: list[injection_api.TestFlight]
    isa_version: str | None = None

    def __init__(self, **kwargs):
        kwargs["flights"] = [
            injection_api.TestFlight(**flight) for flight in kwargs["flights"]
        ]
        for flight in kwargs["flights"]:
            flight.order_telemetry()

        super().__init__(**kwargs)


class Database(ImplicitDict):
    """Simple pseudo-database structure tracking the state of the mock system"""

    tests: dict[str, TestRecord] = {}
    behavior: ServiceProviderBehavior = ServiceProviderBehavior()
    notifications: ServiceProviderUserNotifications = ServiceProviderUserNotifications()


db = SynchronizedValue[Database](
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
