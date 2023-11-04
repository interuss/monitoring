from enum import Enum
from typing import List

from implicitdict import ImplicitDict
from monitoring.monitorlib.clients.flight_planning.flight_info import ExecutionStyle
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentID,
)


class AcceptanceExpectation(str, Enum):
    MustBeRejected = "MustBeRejected"
    """When a flight planner service provider is requested to accept the flight described in this step, the service provider must decline to create the flight.  Accepting the flight successfully will cause a failed check."""

    MustBeAccepted = "MustBeAccepted"
    """When a flight planner service provider is requested to accept the flight described in this step, the service provider must successfully create the flight.  Declining to authorize the flight will cause a failed check."""

    Irrelevant = "Irrelevant"
    """The service provider may choose to accept the flight or not.  Presumably this option would be accompanied by a specific conditions_expectation to ensure that conditions were present (or absent) if the flight were accepted."""


class ConditionsExpectation(str, Enum):
    Irrelevant = "Irrelevant"
    """Whether conditions accompanying the flight planning attempt are present is irrelevant to this feature check."""

    MustBePresent = "MustBePresent"
    """If the flight is accepted, it must be accompanied by some conditions/advisories.  If the flight is not accepted, whether conditions are present is irrelevant."""

    MustBeAbsent = "MustBeAbsent"
    """If the flight is accepted, it must be unconditional (no accompanying conditions).  If the flight is not accepted, whether conditions are present is irrelevant."""


class FlightCheck(ImplicitDict):
    flight_check_id: str
    """Unique (within table) test step/row identifier."""

    requirement_ids: List[str]
    """Jurisdictional identifiers of the requirements this test step is evaluating."""

    description: str
    """Human-readable test step description to aid in the debugging and traceability."""

    flight_intent: FlightIntentID
    """ID of the flight intent, as a user would provide it to the USS, referring to one of the flight intents provided in a separate dictionary relating FlightIntentID to FlightInfoTemplate."""

    execution_style: ExecutionStyle
    """The manner in which the USS should be instructed to plan the flight."""

    acceptance_expectation: AcceptanceExpectation = AcceptanceExpectation.Irrelevant
    """Expected outcome when authorizing a flight as described."""

    conditions_expectation: ConditionsExpectation = ConditionsExpectation.Irrelevant
    """Expected conditions/advisories produced when authorizing a flight as described."""


class FlightCheckTable(ImplicitDict):
    rows: List[FlightCheck]
