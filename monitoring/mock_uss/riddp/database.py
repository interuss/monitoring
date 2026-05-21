import json

from implicitdict import ImplicitDict

from monitoring.monitorlib.fetch.rid import ISA
from monitoring.monitorlib.geo import LatLngBoundingBox
from monitoring.monitorlib.multiprocessing import SynchronizedValue
from monitoring.monitorlib.mutate.rid import ChangedSubscription, UpdatedISA

from .behavior import DisplayProviderBehavior


class FlightInfo(ImplicitDict):
    flights_url: str


class ObservationSubscription(ImplicitDict):
    bounds: LatLngBoundingBox

    upsert_result: ChangedSubscription

    updates: list[UpdatedISA]

    def get_isas(self) -> list[ISA]:
        isas = [isa for isa in self.upsert_result.isas]
        # TODO: consider sorting updates by notification index
        for update in self.updates:
            current_isas = []
            isa_already_exists = False
            for isa in isas:
                if update.isa_id == isa.id:
                    isa_already_exists = True
                    if update.isa is not None:
                        current_isas.append(update.isa)
                    else:
                        pass  # Exclude this ISA since the update removed it
                else:
                    current_isas.append(isa)
            if not isa_already_exists:
                current_isas.append(update.isa)
            isas = current_isas
        return isas

    @property
    def flights_urls(self) -> dict[str, str]:
        """Returns map of flights URL to owning USS"""
        return {isa.flights_url: isa.owner for isa in self.get_isas()}


class Database(ImplicitDict):
    """Simple pseudo-database structure tracking the state of the mock system"""

    flights: dict[str, FlightInfo]
    behavior: DisplayProviderBehavior = DisplayProviderBehavior()
    subscriptions: list[ObservationSubscription]


db = SynchronizedValue[Database](
    Database(flights={}, subscriptions=[]),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
