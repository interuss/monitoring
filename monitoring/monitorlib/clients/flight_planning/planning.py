from __future__ import annotations
from enum import Enum
from typing import Optional, List, Dict

from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21 import api as f3548v21
from uas_standards.interuss.automated_testing.scd.v1 import api as scd_api

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    FlightID,
    FlightInfo,
    UasState,
    AirspaceUsageState,
)
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

    @staticmethod
    def from_flightinfo(info: Optional[FlightInfo]) -> FlightPlanStatus:
        if info is None:
            return FlightPlanStatus.NotPlanned
        if info.basic_information.uas_state != UasState.Nominal:
            return FlightPlanStatus.OffNominal
        if info.basic_information.usage_state == AirspaceUsageState.InUse:
            return FlightPlanStatus.OkToFly
        return FlightPlanStatus.Planned


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

    notes: Optional[str]
    """Any human-readable notes regarding the activity."""

    includes_advisories: Optional[AdvisoryInclusion] = AdvisoryInclusion.Unknown

    def to_inject_flight_response(self) -> scd_api.InjectFlightResponse:
        if self.activity_result == PlanningActivityResult.Completed:
            if self.flight_plan_status == FlightPlanStatus.Planned:
                result = scd_api.InjectFlightResponseResult.Planned
            elif self.flight_plan_status == FlightPlanStatus.OkToFly:
                result = scd_api.InjectFlightResponseResult.ReadyToFly
            elif self.flight_plan_status == FlightPlanStatus.OffNominal:
                result = scd_api.InjectFlightResponseResult.ReadyToFly
            elif self.flight_plan_status == FlightPlanStatus.NotPlanned:
                raise ValueError(
                    "Cannot represent PlanningActivityResponse of {Completed, NotPlanned} as an scd injection API InjectFlightResponseResult"
                )
            elif self.flight_plan_status == FlightPlanStatus.Closed:
                raise ValueError(
                    "Cannot represent PlanningActivityResponse of {Completed, Closed} as an scd injection API InjectFlightResponseResult"
                )
            else:
                raise ValueError(
                    f"Invalid `flight_plan_status` '{self.flight_plan_status}' in PlanningActivityResponse"
                )
        elif self.activity_result == PlanningActivityResult.Rejected:
            result = scd_api.InjectFlightResponseResult.Rejected
        elif self.activity_result == PlanningActivityResult.Failed:
            result = scd_api.InjectFlightResponseResult.Failed
        elif self.activity_result == PlanningActivityResult.NotSupported:
            result = scd_api.InjectFlightResponseResult.NotSupported
        else:
            raise ValueError(
                f"Invalid `activity_result` '{self.activity_result}' in PlanningActivityResponse"
            )
        notes = {"notes": self.notes} if "notes" in self else {}
        return scd_api.InjectFlightResponse(result=result, **notes)


class ClearAreaResponse(ImplicitDict):
    flights_deleted: List[FlightID]
    """List of IDs of flights that were deleted during this area clearing operation."""

    flight_deletion_errors: Dict[FlightID, dict]
    """When an error was encountered deleting a particular flight, information about that error."""

    op_intents_removed: List[f3548v21.EntityOVN]
    """List of IDs of ASTM F3548-21 operational intent references that were removed during this area clearing operation."""

    op_intent_removal_errors: Dict[f3548v21.EntityOVN, dict]
    """When an error was encountered removing a particular operational intent reference, information about that error."""

    error: Optional[dict] = None
    """If an error was encountered that could not be linked to a specific flight or operational intent, information about it will be populated here."""

    @property
    def success(self) -> bool:
        return (
            not self.flight_deletion_errors
            and not self.op_intent_removal_errors
            and self.error is None
        )
