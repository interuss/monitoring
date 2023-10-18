from datetime import datetime
from typing import List, Optional

from implicitdict import ImplicitDict

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
    ASTMF354821OpIntentInformation,
    FlightAuthorisationData,
    RPAS26FlightDetails,
    BasicFlightPlanInformation,
    FlightInfo,
)
from monitoring.monitorlib.geotemporal import Volume4DTemplate, resolve_volume4d


class BasicFlightPlanInformationTemplate(ImplicitDict):
    """Template to provide (at runtime) basic information about a flight plan that an operator and/or UAS can be expected to provide in most flight planning scenarios."""

    usage_state: AirspaceUsageState
    """User's current usage of the airspace specified in the flight plan."""

    uas_state: UasState
    """State of the user's UAS associated with this flight plan."""

    area: List[Volume4DTemplate]
    """User intends to or may fly anywhere in this entire area."""

    def resolve(self, start_of_test: datetime) -> BasicFlightPlanInformation:
        kwargs = {k: v for k, v in self.items()}
        kwargs["area"] = [resolve_volume4d(t, start_of_test) for t in self.area]
        return ImplicitDict.parse(kwargs, BasicFlightPlanInformation)


class FlightInfoTemplate(ImplicitDict):
    """Template to provide (at runtime) details of user's intent to create or modify a flight plan."""

    basic_information: BasicFlightPlanInformationTemplate

    astm_f3548_21: Optional[ASTMF354821OpIntentInformation]

    uspace_flight_authorisation: Optional[FlightAuthorisationData]

    rpas_operating_rules_2_6: Optional[RPAS26FlightDetails]

    additional_information: Optional[dict]
    """Any information relevant to a particular jurisdiction or use case not described in the standard schema. The keys and values must be agreed upon between the test designers and USSs under test."""

    def resolve(self, start_of_test: datetime) -> FlightInfo:
        kwargs = {k: v for k, v in self.items()}
        kwargs["basic_information"] = self.basic_information.resolve(start_of_test)
        return ImplicitDict.parse(kwargs, FlightInfo)
