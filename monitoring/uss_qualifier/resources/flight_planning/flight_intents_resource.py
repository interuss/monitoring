from datetime import timedelta
import json
from typing import Dict

import arrow
from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.resources.overrides import apply_overrides
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentCollection,
    FlightIntentsSpecification,
    FlightIntent,
    FlightIntentID,
)


class FlightIntentsResource(Resource[FlightIntentsSpecification]):
    _planning_time: timedelta
    _intent_collection: FlightIntentCollection

    def __init__(self, specification: FlightIntentsSpecification):
        self._intent_collection = ImplicitDict.parse(
            load_dict_with_references(specification.file_source), FlightIntentCollection
        )
        self._planning_time = specification.planning_time.timedelta

    def get_flight_intents(self) -> Dict[FlightIntentID, FlightIntent]:
        """Resolve the underlying delta flight intents and shift appropriately times."""

        t0 = arrow.utcnow() + self._planning_time
        intents: Dict[FlightIntentID, FlightIntent] = {}

        for intent_id, intent_orig in self._intent_collection.intents.items():
            intent: FlightIntent

            # copy intent and resolve delta
            if intent_orig.has_field_with_value("full"):
                intent = ImplicitDict.parse(
                    json.loads(json.dumps(intent_orig.full)), FlightIntent
                )

            elif (
                intent_orig.has_field_with_value("delta_source")
                and intent_orig.delta_source in self._intent_collection.intents
                and self._intent_collection.intents[
                    intent_orig.delta_source
                ].has_field_with_value("full")
                and intent_orig.has_field_with_value("delta_mutation")
            ):
                intent = apply_overrides(
                    self._intent_collection.intents[intent_orig.delta_source].full,
                    intent_orig.delta_mutation,
                )

            else:
                raise ValueError(f"{intent_id} is invalid")

            # shift times
            dt = t0 - intent.reference_time.datetime
            for volume in (
                intent.request.operational_intent.volumes
                + intent.request.operational_intent.off_nominal_volumes
            ):
                volume.time_start.value = StringBasedDateTime(
                    volume.time_start.value.datetime + dt
                )
                volume.time_end.value = StringBasedDateTime(
                    volume.time_end.value.datetime + dt
                )

            intents[intent_id] = intent
        return intents
