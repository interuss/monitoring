from __future__ import annotations
import json
from typing import List, Optional, Dict

from implicitdict import ImplicitDict, StringBasedDateTime, StringBasedTimeDelta
from monitoring.monitorlib.scd import Volume4D

from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    InjectFlightRequest,
)
from monitoring.uss_qualifier.fileio import FileReference


class FlightIntentMutation(ImplicitDict):
    """Represents a mutation of a FlightIntent."""

    state: Optional[str]
    """Mutation of the operational intent state."""

    priority: Optional[int]
    """Mutation of the operational intent priority."""

    volumes: Optional[List[Volume4D]]
    """Mutation of the operational intent volumes.
    Note: the list length must match the original. The subfields will be mutated."""

    off_nominal_volumes: Optional[List[Volume4D]]
    """Mutation of the operational intent off_nominal_volumes.
    Note: the list length must match the original. The subfields will be mutated."""


class FlightIntent(ImplicitDict):
    reference_time: StringBasedDateTime
    """The time that all other times in the FlightInjectionAttempt are relative to. If this FlightInjectionAttempt is initiated by uss_qualifier at t_test, then each t_volume_original timestamp within test_injection should be adjusted to t_volume_adjusted such that t_volume_adjusted = t_test + planning_time when t_volume_original = reference_time"""

    request: InjectFlightRequest
    """Definition of the flight the user wants to create."""

    mutations: Dict[str, FlightIntentMutation] = {}
    """Named mutations of the flight to performed during the test execution."""

    def get_mutated(self, mutation_key: str) -> FlightIntent:
        """Creates a copy of the FlightIntent and apply the mutation provided as parameter.
        Note that a distinction is made between a non-existing field and a field with a None value: a non-existing field
        is left untouched, while a field with a None value is explicitly removed.

        Returns: a mutated copy of this FlightIntent."""

        if mutation_key not in self.mutations:
            raise ValueError(f"{mutation_key} is not part of the mutations")

        mutated: FlightIntent = ImplicitDict.parse(
            json.loads(json.dumps(self)), FlightIntent
        )
        mutation = self.mutations[mutation_key]

        if "state" in mutation:
            mutated.request.operational_intent.state = mutation.state

        if "priority" in mutation:
            mutated.request.operational_intent.priority = mutation.priority

        if "volumes" in mutation:
            for idx, volume in enumerate(mutation.volumes):
                if "time_start" in volume:
                    mutated.request.operational_intent.volumes[
                        idx
                    ].time_start = volume.time_start
                if "time_end" in volume:
                    mutated.request.operational_intent.volumes[
                        idx
                    ].time_end = volume.time_end
                if "outline_circle" in volume.volume:
                    mutated.request.operational_intent.volumes[
                        idx
                    ].volume.outline_circle = volume.volume.outline_circle
                if "outline_polygon" in volume.volume:
                    mutated.request.operational_intent.volumes[
                        idx
                    ].volume.outline_polygon = volume.volume.outline_polygon
                if "altitude_lower" in volume.volume:
                    mutated.request.operational_intent.volumes[
                        idx
                    ].volume.altitude_lower = volume.volume.altitude_lower
                if "altitude_upper" in volume.volume:
                    mutated.request.operational_intent.volumes[
                        idx
                    ].volume.altitude_upper = volume.volume.altitude_upper

        if "off_nominal_volumes" in mutation:
            for idx, volume in enumerate(mutation.off_nominal_volumes):
                if "time_start" in volume:
                    mutated.request.operational_intent.off_nominal_volumes[
                        idx
                    ].time_start = volume.time_start
                if "time_end" in volume:
                    mutated.request.operational_intent.off_nominal_volumes[
                        idx
                    ].time_end = volume.time_end
                if "outline_circle" in volume.volume:
                    mutated.request.operational_intent.off_nominal_volumes[
                        idx
                    ].volume.outline_circle = volume.volume.outline_circle
                if "outline_polygon" in volume.volume:
                    mutated.request.operational_intent.off_nominal_volumes[
                        idx
                    ].volume.outline_polygon = volume.volume.outline_polygon
                if "altitude_lower" in volume.volume:
                    mutated.request.operational_intent.off_nominal_volumes[
                        idx
                    ].volume.altitude_lower = volume.volume.altitude_lower
                if "altitude_upper" in volume.volume:
                    mutated.request.operational_intent.off_nominal_volumes[
                        idx
                    ].volume.altitude_upper = volume.volume.altitude_upper

        return mutated


class FlightIntentCollection(ImplicitDict):
    intents: List[FlightIntent]
    """Flights that users want to create."""


class FlightIntentsSpecification(ImplicitDict):
    planning_time: StringBasedTimeDelta
    """Time delta between the time uss_qualifier initiates this FlightInjectionAttempt and when a timestamp within the test_injection equal to reference_time occurs"""

    file_source: FileReference
    """Location of file to load"""
