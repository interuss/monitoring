from datetime import timedelta
import json
from typing import List

import arrow
from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentCollection,
    FlightIntentsSpecification,
    FlightIntent,
)


class FlightIntentsResource(Resource[FlightIntentsSpecification]):
    _planning_time: timedelta
    _intent_collection: FlightIntentCollection

    def __init__(self, specification: FlightIntentsSpecification):
        self._intent_collection = ImplicitDict.parse(
            load_dict_with_references(specification.file_source), FlightIntentCollection
        )
        self._planning_time = specification.planning_time.timedelta

    def get_flight_intents(self) -> List[FlightIntent]:
        t0 = arrow.utcnow() + self._planning_time

        intents: List[FlightIntent] = []

        for intent in self._intent_collection.intents:
            intent: FlightIntent = ImplicitDict.parse(
                json.loads(json.dumps(intent)), FlightIntent
            )
            dt = t0 - intent.reference_time.datetime

            volumes_to_shift = (
                intent.request.operational_intent.volumes
                + intent.request.operational_intent.off_nominal_volumes
            )
            for mutation in intent.mutations.values():
                if mutation.has_field_with_value("volumes"):
                    volumes_to_shift += mutation.volumes
                if mutation.has_field_with_value("off_nominal_volumes"):
                    volumes_to_shift += mutation.off_nominal_volumes

            for volume in volumes_to_shift:
                volume.time_start.value = StringBasedDateTime(
                    volume.time_start.value.datetime + dt
                )
                volume.time_end.value = StringBasedDateTime(
                    volume.time_end.value.datetime + dt
                )
            intents.append(intent)

        return intents
