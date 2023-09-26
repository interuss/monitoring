from enum import Enum
from typing import Optional, List

from implicitdict import ImplicitDict

from monitoring.monitorlib.clients.flight_planning.flight_info import FlightID
from monitoring.monitorlib.fetch import Query


class PlanningActivityResult(str, Enum):
    """The result of the flight planning operation."""

    Completed = "Completed"
    """The user's flight plan has been updated according to the situation specified by the user."""

    Rejected = "Rejected"
    """The updates the user requested to their flight plan are not allowed according to the rules under which the flight plan is being managed.  The reasons for rejection may include a disallowed conflict with another flight during preflight."""

    Failed = "Failed"
    """The USS was not able to successfully authorize or update the flight plan due to a problem with the USS or a downstream system."""

    NotSupported = "NotSupported"
    """The USS's implementation does not support the attempted interaction.  For instance, if the request specified a high-priority flight and the USS does not support management of high-priority flights."""


class FlightPlanStatus(str, Enum):
    """Status of a user's flight plan."""

    NotPlanned = "NotPlanned"
    """The USS has not created an authorized flight plan for the user."""

    Planned = "Planned"
    """The USS has created an authorized flight plan for the user, but the user may not yet start flying (even if within the time bounds of the flight plan)."""

    OkToFly = "OkToFly"
    """The flight plan is in a state such that it is ok for the user to nominally fly within the bounds (including time) of the flight plan."""

    OffNominal = "OffNominal"
    """The flight plan now reflects the operator's actions, but the flight plan is not in a nominal state (e.g., the USS has placed the ASTM F3548-21 operational intent into one of the Nonconforming or Contingent states)."""

    Closed = "Closed"
    """The flight plan was closed successfully by the USS and is now out of the UTM system."""


class AdvisoryInclusion(str, Enum):
    """Indication of whether any advisories or conditions were provided to the user along with the result of a flight planning attempt."""

    Unknown = "Unknown"
    """It is unknown or irrelevant whether advisories or conditions were provided to the user."""

    AtLeastOneAdvisoryOrCondition = "AtLeastOneAdvisoryOrCondition"
    """At least one advisory or condition was provided to the user."""

    NoAdvisoriesOrConditions = "NoAdvisoriesOrConditions"
    """No advisories or conditions were provided to the user."""


class PlanningActivityResponse(ImplicitDict):
    flight_id: FlightID
    """Identity of flight for which the planning activity was conducted."""

    queries: List[Query]
    """Queries used to accomplish this activity."""

    activity_result: PlanningActivityResult
    """The result of the flight planning activity."""

    flight_plan_status: FlightPlanStatus
    """Status of the flight plan following the flight planning activity."""

    includes_advisories: Optional[AdvisoryInclusion] = AdvisoryInclusion.Unknown
