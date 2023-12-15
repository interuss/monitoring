from typing import Dict, List

from implicitdict import ImplicitDict

from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.geotemporal import Volume4DCollection

from monitoring.uss_qualifier.resources.files import load_dict
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentCollection,
    FlightIntentsSpecification,
    FlightIntentID,
    FlightIntent,
)


class FlightIntentsResource(Resource[FlightIntentsSpecification]):
    _intent_collection: FlightIntentCollection

    def __init__(self, specification: FlightIntentsSpecification):
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


def unpack_flight_intents(
    flight_intents: FlightIntentsResource, flight_identifiers: List[str]
):
    """
    Extracts the specified flight identifiers from the passed FlightIntentsResource
    """
    flight_intents = {
        k: FlightIntent.from_flight_info_template(v)
        for k, v in flight_intents.get_flight_intents().items()
        if k in flight_identifiers
    }

    extents = []
    for intent in flight_intents.values():
        extents.extend(intent.request.operational_intent.volumes)
        extents.extend(intent.request.operational_intent.off_nominal_volumes)

    intents_extent = Volume4DCollection.from_interuss_scd_api(
        extents
    ).bounding_volume.to_f3548v21()

    return intents_extent, flight_intents
