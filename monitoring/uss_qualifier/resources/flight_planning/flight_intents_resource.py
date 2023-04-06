from datetime import timedelta
import json
from typing import Dict

import arrow
import bc_jsonpath_ng.ext
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


_time_finder = bc_jsonpath_ng.ext.parse("$..[time_start,time_end].value.`parent`")


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

        # process intents in order of dependency
        processed_intents: Dict[FlightIntentID, FlightIntent] = {}
        unprocessed_intent_ids = list(self._intent_collection.intents.keys())

        while unprocessed_intent_ids:
            nb_processed = 0
            for intent_id in unprocessed_intent_ids:
                unprocessed_intent = self._intent_collection.intents[intent_id]
                processed_intent: FlightIntent

                # copy intent and resolve delta
                if unprocessed_intent.has_field_with_value("full"):
                    processed_intent = ImplicitDict.parse(
                        json.loads(json.dumps(unprocessed_intent.full)), FlightIntent
                    )
                    times_to_shift = [
                        m.value for m in _time_finder.find(processed_intent)
                    ]

                elif unprocessed_intent.has_field_with_value("delta"):
                    if unprocessed_intent.delta.source not in processed_intents:
                        # delta source has not been processed yet
                        continue

                    processed_intent = ImplicitDict.parse(
                        apply_overrides(
                            processed_intents[unprocessed_intent.delta.source],
                            unprocessed_intent.delta.mutation,
                        ),
                        FlightIntent,
                    )
                    times_to_shift = []
                    for unprocessed_match in _time_finder.find(
                        unprocessed_intent.delta.mutation
                    ):
                        processed_matches = unprocessed_match.full_path.find(
                            processed_intent
                        )
                        if processed_matches:
                            times_to_shift.append(processed_matches[0].value)

                else:
                    raise ValueError(f"{intent_id} is invalid")

                # shift times
                dt = t0 - processed_intent.reference_time.datetime
                for t in times_to_shift:
                    t.value = StringBasedDateTime(t.value.datetime + dt)

                nb_processed += 1
                processed_intents[intent_id] = processed_intent
                unprocessed_intent_ids.remove(intent_id)

            if nb_processed == 0 and unprocessed_intent_ids:
                raise ValueError(
                    "Unresolvable dependency detected between intents: "
                    + ", ".join(i_id for i_id in unprocessed_intent_ids)
                )

        return processed_intents
