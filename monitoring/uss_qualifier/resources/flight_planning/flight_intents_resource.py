from typing import Dict

from implicitdict import ImplicitDict

from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.uss_qualifier.resources.files import load_dict
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentCollection,
    FlightIntentID,
    FlightIntentsSpecification,
)
from monitoring.uss_qualifier.resources.resource import Resource


class FlightIntentsResource(Resource[FlightIntentsSpecification]):
    _intent_collection: FlightIntentCollection

    def __init__(self, specification: FlightIntentsSpecification, resource_origin: str):
        super(FlightIntentsResource, self).__init__(specification, resource_origin)
        has_file = "file" in specification and specification.file
        has_literal = (
            "intent_collection" in specification and specification.intent_collection
        )
        if has_file and has_literal:
            raise ValueError(
                "Only one of `file` or `intent_collection` may be specified in FlightIntentsSpecification"
            )
        if not has_file and not has_literal:
            raise ValueError(
                "One of `file` or `intent_collection` must be specified in FlightIntentsSpecification"
            )
        if has_file:
            self._intent_collection = ImplicitDict.parse(
                load_dict(specification.file), FlightIntentCollection
            )
        elif has_literal:
            self._intent_collection = specification.intent_collection
        if "transformations" in specification and specification.transformations:
            if (
                "transformations" in self._intent_collection
                and self._intent_collection.transformations
            ):
                self._intent_collection.transformations.extend(
                    specification.transformations
                )
            else:
                self._intent_collection.transformations = specification.transformations

    def get_flight_intents(self) -> Dict[FlightIntentID, FlightInfoTemplate]:
        return self._intent_collection.resolve()
