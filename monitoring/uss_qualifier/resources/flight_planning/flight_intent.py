from __future__ import annotations

import json
from typing import Optional, Dict, List

import arrow

from implicitdict import ImplicitDict, StringBasedDateTime
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.monitorlib.transformations import Transformation

from monitoring.uss_qualifier.resources.files import ExternalFile
from monitoring.uss_qualifier.resources.overrides import apply_overrides
from uas_standards.interuss.automated_testing.scd.v1.api import InjectFlightRequest


class FlightIntent(ImplicitDict):
    """DEPRECATED.  Use FlightInfoTemplate instead."""

    reference_time: StringBasedDateTime
    """The time that all other times in the FlightInjectionAttempt are relative to. If this FlightInjectionAttempt is initiated by uss_qualifier at t_test, then each t_volume_original timestamp within test_injection should be adjusted to t_volume_adjusted such that t_volume_adjusted = t_test + planning_time when t_volume_original = reference_time"""

    request: InjectFlightRequest
    """Definition of the flight the user wants to create."""

    @staticmethod
    def from_flight_info_template(info_template: FlightInfoTemplate) -> FlightIntent:
        t_now = Time(arrow.utcnow().datetime)
        times = {
            TimeDuringTest.StartOfTestRun: t_now,
            TimeDuringTest.StartOfScenario: t_now,
            TimeDuringTest.TimeOfEvaluation: t_now,
        }  # Not strictly correct, but this class is deprecated
        request = info_template.to_scd_inject_request(times)
        return FlightIntent(reference_time=StringBasedDateTime(t_now), request=request)


FlightIntentID = str
"""Identifier for a flight planning intent within a collection of flight planning intents.

To be used only within uss_qualifier (not visible to participants under test) to select an appropriate flight planning intent from the collection."""


class DeltaFlightIntent(ImplicitDict):
    """Represents an intent expressed as identical to another intent except for some specific changes."""

    source: FlightIntentID
    """Base the flight intent for this element of a FlightIntentCollection on the element of the collection identified by this field."""

    mutation: Optional[dict]
    """For each leaf subfield specified in this object, override the value in the corresponding subfield of the flight intent for this element with the specified value.

    Consider subfields prefixed with + as leaf subfields."""


class FlightIntentCollectionElement(ImplicitDict):
    """Definition of a single flight intent within a FlightIntentCollection.  Exactly one field must be specified."""

    full: Optional[FlightInfoTemplate]
    """If specified, the full definition of the flight planning intent."""

    delta: Optional[DeltaFlightIntent]
    """If specified, a flight planning intent based on another flight intent, but with some changes."""


class FlightIntentCollection(ImplicitDict):
    """Specification for a collection of flight intents, each identified by a FlightIntentID."""

    intents: Dict[FlightIntentID, FlightIntentCollectionElement]
    """Flight planning actions that users want to perform."""

    transformations: Optional[List[Transformation]]
    """Transformations to append to all FlightInfoTemplates."""

    def resolve(self) -> Dict[FlightIntentID, FlightInfoTemplate]:
        """Resolve the underlying delta flight intents."""

        # process intents in order of dependency to resolve deltas
        processed_intents: Dict[FlightIntentID, FlightInfoTemplate] = {}
        unprocessed_intent_ids = list(self.intents.keys())

        while unprocessed_intent_ids:
            nb_processed = 0
            for intent_id in unprocessed_intent_ids:
                unprocessed_intent = self.intents[intent_id]
                processed_intent: FlightInfoTemplate

                # copy intent and resolve delta
                if unprocessed_intent.has_field_with_value("full"):
                    processed_intent = ImplicitDict.parse(
                        json.loads(json.dumps(unprocessed_intent.full)),
                        FlightInfoTemplate,
                    )
                elif unprocessed_intent.has_field_with_value("delta"):
                    if unprocessed_intent.delta.source not in processed_intents:
                        # delta source has not been processed yet
                        continue

                    processed_intent = apply_overrides(
                        processed_intents[unprocessed_intent.delta.source],
                        unprocessed_intent.delta.mutation,
                    )
                else:
                    raise ValueError(
                        f"{intent_id} flight intent in FlightIntentCollection is invalid; must specify `full` or `delta`"
                    )

                nb_processed += 1
                processed_intents[intent_id] = processed_intent
                unprocessed_intent_ids.remove(intent_id)

            if nb_processed == 0 and unprocessed_intent_ids:
                raise ValueError(
                    "Unresolvable dependency detected between intents: "
                    + ", ".join(i_id for i_id in unprocessed_intent_ids)
                )

        if "transformations" in self and self.transformations:
            for v in processed_intents.values():
                xforms = (
                    v.transformations.copy()
                    if v.has_field_with_value("transformations")
                    else []
                )
                xforms.extend(self.transformations)
                v.transformations = xforms

        return processed_intents


class FlightIntentsSpecification(ImplicitDict):
    """Exactly one field must be specified."""

    intent_collection: Optional[FlightIntentCollection]
    """Full flight intent collection, or a $ref to an external file containing a FlightIntentCollection."""

    file: Optional[ExternalFile]
    """Location of file to load, containing a FlightIntentCollection"""

    transformations: Optional[List[Transformation]]
    """Transformations to apply to all flight intents' 4D volumes after resolution (if specified)"""
