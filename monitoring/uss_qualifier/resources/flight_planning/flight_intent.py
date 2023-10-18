from typing import Optional, Dict

from implicitdict import ImplicitDict, StringBasedDateTime, StringBasedTimeDelta

from monitoring.uss_qualifier.fileio import FileReference
from monitoring.uss_qualifier.resources.files import ExternalFile
from uas_standards.interuss.automated_testing.scd.v1.api import InjectFlightRequest


class FlightIntent(ImplicitDict):
    reference_time: StringBasedDateTime
    """The time that all other times in the FlightInjectionAttempt are relative to. If this FlightInjectionAttempt is initiated by uss_qualifier at t_test, then each t_volume_original timestamp within test_injection should be adjusted to t_volume_adjusted such that t_volume_adjusted = t_test + planning_time when t_volume_original = reference_time"""

    request: InjectFlightRequest
    """Definition of the flight the user wants to create."""


FlightIntentID = str
"""Identifier for a flight intent within a collection of flight intents.

To be used only within uss_qualifier (not visible to participants under test) to select an appropriate flight intent from the collection."""


class DeltaFlightIntent(ImplicitDict):
    """Represents an intent expressed as identical to another intent except for some specific changes."""

    source: FlightIntentID
    """Base the flight intent for this element of a FlightIntentCollection on the element of the collection identified by this field."""

    mutation: Optional[dict]
    """For each subfield specified in this object, override the value in the corresponding subfield of the flight intent for this element with the specified value."""


class FlightIntentCollectionElement(ImplicitDict):
    """Definition of a single flight intent within a FlightIntentCollection.  Exactly one field must be specified."""

    full: Optional[FlightIntent]
    """If specified, the full definition of the flight intent."""

    delta: Optional[DeltaFlightIntent]
    """If specified, a flight intent based on another flight intent, but with some changes."""


class FlightIntentCollection(ImplicitDict):
    """Specification for a collection of flight intents, each identified by a FlightIntentID."""

    intents: Dict[FlightIntentID, FlightIntentCollectionElement]
    """Flights that users want to create."""


class FlightIntentsSpecification(ImplicitDict):
    planning_time: StringBasedTimeDelta
    """Time delta between the time uss_qualifier initiates this FlightInjectionAttempt and when a timestamp within the test_injection equal to reference_time occurs"""

    file: ExternalFile
    """Location of file to load"""
