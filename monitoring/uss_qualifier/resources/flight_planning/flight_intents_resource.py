import json
from typing import Dict

from implicitdict import ImplicitDict
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)

from monitoring.uss_qualifier.resources.files import load_dict
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentCollection,
    FlightIntentsSpecification,
    FlightIntentID,
)


class FlightIntentsResource(Resource[FlightIntentsSpecification]):
    _intent_collection: FlightIntentCollection

    def __init__(self, specification: FlightIntentsSpecification):
        self._intent_collection = ImplicitDict.parse(
            load_dict(specification.file), FlightIntentCollection
        )

    def get_flight_intents(self) -> Dict[FlightIntentID, FlightInfoTemplate]:
        return self._intent_collection.resolve()
