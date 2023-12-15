from typing import Optional, Dict, List

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
from monitoring.monitorlib.geo import LatLngPoint
from monitoring.monitorlib.geotemporal import (
    Volume4DTemplateCollection,
    Volume4DCollection,
)
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.monitorlib.transformations import Transformation
from uas_standards.interuss.automated_testing.scd.v1 import api as scd_api


class BasicFlightPlanInformationTemplate(ImplicitDict):
    """Template to provide (at runtime) basic information about a flight plan that an operator and/or UAS can be expected to provide in most flight planning scenarios."""

    usage_state: AirspaceUsageState
    """User's current usage of the airspace specified in the flight plan."""

    uas_state: UasState
    """State of the user's UAS associated with this flight plan."""

    area: Volume4DTemplateCollection
    """User intends to or may fly anywhere in this entire area."""

    def resolve(self, times: Dict[TimeDuringTest, Time]) -> BasicFlightPlanInformation:
        kwargs = {k: v for k, v in self.items()}
        kwargs["area"] = Volume4DCollection([t.resolve(times) for t in self.area])
        return ImplicitDict.parse(kwargs, BasicFlightPlanInformation)


class FlightInfoTemplate(ImplicitDict):
    """Template to provide (at runtime) details of user's intent to create or modify a flight plan."""

    basic_information: BasicFlightPlanInformationTemplate

    astm_f3548_21: Optional[ASTMF354821OpIntentInformation]

    uspace_flight_authorisation: Optional[FlightAuthorisationData]

    rpas_operating_rules_2_6: Optional[RPAS26FlightDetails]

    additional_information: Optional[dict]
    """Any information relevant to a particular jurisdiction or use case not described in the standard schema. The keys and values must be agreed upon between the test designers and USSs under test."""

    transformations: Optional[List[Transformation]]
    """If specified, transform this flight according to these transformations in order (after all templates are resolved)."""

    def resolve(self, times: Dict[TimeDuringTest, Time]) -> FlightInfo:
        kwargs = {k: v for k, v in self.items() if k not in {"transformations"}}
        basic_info = self.basic_information.resolve(times)
        if "transformations" in self and self.transformations:
            for xform in self.transformations:
                basic_info.area = [v.transform(xform) for v in basic_info.area]
        kwargs["basic_information"] = basic_info
        return ImplicitDict.parse(kwargs, FlightInfo)

    def to_scd_inject_request(
        self, times: Dict[TimeDuringTest, Time]
    ) -> scd_api.InjectFlightRequest:
        """Render a legacy SCD injection API request object from this object."""

        info = self.resolve(times)
        if "astm_f3548_21" not in info or not info.astm_f3548_21:
            raise ValueError(
                f"Legacy SCD injection API requires astm_f3548_21 operational intent priority to be specified in FlightInfo"
            )
        if (
            "uspace_flight_authorisation" not in info
            or not info.uspace_flight_authorisation
        ):
            raise ValueError(
                f"Legacy SCD injection API requires uspace_flight_authorisation to be specified in FlightInfo"
            )
        volumes = [v.to_interuss_scd_api() for v in info.basic_information.area]
        off_nominal_volumes = []
        state = scd_api.OperationalIntentState(
            info.basic_information.f3548v21_op_intent_state()
        )
        if state in (
            scd_api.OperationalIntentState.Nonconforming,
            scd_api.OperationalIntentState.Contingent,
        ):
            off_nominal_volumes = volumes
            volumes = []
        operational_intent = scd_api.OperationalIntentTestInjection(
            state=state,
            priority=scd_api.Priority(info.astm_f3548_21.priority),
            volumes=volumes,
            off_nominal_volumes=off_nominal_volumes,
        )
        flight_authorisation = ImplicitDict.parse(
            info.uspace_flight_authorisation, scd_api.FlightAuthorisationData
        )
        return scd_api.InjectFlightRequest(
            operational_intent=operational_intent,
            flight_authorisation=flight_authorisation,
        )
