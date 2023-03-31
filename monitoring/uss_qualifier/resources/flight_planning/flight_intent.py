from typing import Optional, Dict

from implicitdict import ImplicitDict, StringBasedDateTime, StringBasedTimeDelta

from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    InjectFlightRequest,
)
from monitoring.uss_qualifier.fileio import FileReference


class FlightIntent(ImplicitDict):
    reference_time: StringBasedDateTime
    """The time that all other times in the FlightInjectionAttempt are relative to. If this FlightInjectionAttempt is initiated by uss_qualifier at t_test, then each t_volume_original timestamp within test_injection should be adjusted to t_volume_adjusted such that t_volume_adjusted = t_test + planning_time when t_volume_original = reference_time"""

    request: InjectFlightRequest
    """Definition of the flight the user wants to create."""


FlightIntentID = str
"""Identifier for a flight intent within a collection of flight intents.

To be used only within uss_qualifier (not visible to participants under test) to select an appropriate flight intent from the collection."""


class FlightIntentCollectionElement(ImplicitDict):
    """Definition of a single flight intent within a FlightIntentCollection.  Exactly `full_intent` OR [`delta_source` AND `delta_mutation`] must be specified.
    A delta flight intent represents an intent expressed as identical to another intent except for some specific changes."""

    full: Optional[FlightIntent]
    """If specified, the full definition of the flight intent."""

    delta_source: Optional[FlightIntentID]
    """If specified alongside delta_mutation, base the flight intent for this element of the collection on the element of the collection identified by this field."""

    delta_mutation: Optional[dict]
    """If specified alongside delta_source, for each subfield specified in this object, override the value in the corresponding subfield of the flight intent for this element with the specified value."""


class FlightIntentCollection(ImplicitDict):
    """Specification for a collection of flight intents, each identified by a FlightIntentID."""

    intents: Dict[FlightIntentID, FlightIntentCollectionElement]
    """Flights that users want to create."""


class FlightIntentsSpecification(ImplicitDict):
    planning_time: StringBasedTimeDelta
    """Time delta between the time uss_qualifier initiates this FlightInjectionAttempt and when a timestamp within the test_injection equal to reference_time occurs"""

    file_source: FileReference
    """Location of file to load"""
