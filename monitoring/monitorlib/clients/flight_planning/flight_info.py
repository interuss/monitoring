from __future__ import annotations
from enum import Enum
from typing import Optional, List

from implicitdict import ImplicitDict
from uas_standards.ansi_cta_2063_a import SerialNumber
from uas_standards.en4709_02 import OperatorRegistrationNumber
from uas_standards.interuss.automated_testing.scd.v1 import api as scd_api

from monitoring.monitorlib.geotemporal import Volume4D, Volume4DCollection

# ===== ASTM F3548-21 =====


Priority = int
"""Ordinal priority that the flight's operational intent should be assigned, as defined in ASTM F3548-21."""


class ASTMF354821OpIntentInformation(ImplicitDict):
    """Information provided about a flight plan that is necessary for ASTM F3548-21."""

    priority: Optional[Priority]


# ===== U-space =====


class FlightAuthorisationDataOperationCategory(str, Enum):
    """Category of UAS operation (‘open’, ‘specific’, ‘certified’) as defined in COMMISSION DELEGATED REGULATION (EU) 2019/945. Required by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 4."""

    Unknown = "Unknown"
    Open = "Open"
    Specific = "Specific"
    Certified = "Certified"


class OperationMode(str, Enum):
    """Specify if the operation is a `VLOS` or `BVLOS` operation. Required by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 2."""

    Undeclared = "Undeclared"
    Vlos = "Vlos"
    Bvlos = "Bvlos"


class UASClass(str, Enum):
    """Specify the class of the UAS to be flown, the specifition matches EASA class identification label categories. UAS aircraft class as defined in COMMISSION DELEGATED REGULATION (EU) 2019/945 (C0 to C4) and COMMISSION DELEGATED REGULATION (EU) 2020/1058 (C5 and C6). This field is required by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 4."""

    Other = "Other"
    C0 = "C0"
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"
    C6 = "C6"


class FlightAuthorisationData(ImplicitDict):
    """The details of a UAS flight authorization request, as received from the user.

    Note that a full description of a flight authorisation must include mandatory information required by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664 for an UAS flight authorisation request. Reference: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32021R0664&from=EN#d1e32-178-1
    """

    uas_serial_number: SerialNumber
    """Unique serial number of the unmanned aircraft or, if the unmanned aircraft is privately built, the unique serial number of the add-on. This is expressed in the ANSI/CTA-2063 Physical Serial Number format. Required by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 1."""

    operation_mode: OperationMode

    operation_category: FlightAuthorisationDataOperationCategory
    """Category of UAS operation (‘open’, ‘specific’, ‘certified’) as defined in COMMISSION DELEGATED REGULATION (EU) 2019/945. Required by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 4."""

    uas_class: UASClass

    identification_technologies: List[str]
    """Technology used to identify the UAS. Required by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 6."""

    uas_type_certificate: Optional[str]
    """Provisional field. Not applicable as of September 2021. Required only if `uas_class` is set to `other` by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 4."""

    connectivity_methods: List[str]
    """Connectivity methods. Required by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 7."""

    endurance_minutes: int
    """Endurance of the UAS. This is expressed in minutes. Required by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 8."""

    emergency_procedure_url: str
    """The URL at which the applicable emergency procedure in case of a loss of command and control link may be retrieved. Required by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 9."""

    operator_id: OperatorRegistrationNumber
    """Registration number of the UAS operator.
    The format is defined in EASA Easy Access Rules for Unmanned Aircraft Systems GM1 to AMC1
    Article 14(6) Registration of UAS operators and ‘certified’ UAS.
    Required by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 10.
    """

    uas_id: Optional[str]
    """When applicable, the registration number of the unmanned aircraft.
    This is expressed using the nationality and registration mark of the unmanned aircraft in
    line with ICAO Annex 7.
    Specified by ANNEX IV of COMMISSION IMPLEMENTING REGULATION (EU) 2021/664, paragraph 10.
    """


# ===== RPAS Operating Rules 2.6 =====


class RPAS26FlightDetailsOperatorType(str, Enum):
    """The type of operator."""

    Recreational = "Recreational"
    CommercialExcluded = "CommercialExcluded"
    ReOC = "ReOC"


class RPAS26FlightDetailsAircraftType(str, Enum):
    """Type of vehicle being used as per ASTM F3411-22a."""

    NotDeclared = "NotDeclared"
    Aeroplane = "Aeroplane"
    Helicopter = "Helicopter"
    Gyroplane = "Gyroplane"
    HybridLift = "HybridLift"
    Ornithopter = "Ornithopter"
    Glider = "Glider"
    Kite = "Kite"
    FreeBalloon = "FreeBalloon"
    CaptiveBalloon = "CaptiveBalloon"
    Airship = "Airship"
    FreeFallOrParachute = "FreeFallOrParachute"
    Rocket = "Rocket"
    TetheredPoweredAircraft = "TetheredPoweredAircraft"
    GroundObstacle = "GroundObstacle"
    Other = "Other"


class RPAS26FlightDetailsFlightProfile(str, Enum):
    """Type of flight profile."""

    AutomatedGrid = "AutomatedGrid"
    AutomatedWaypoint = "AutomatedWaypoint"
    Manual = "Manual"


class RPAS26FlightDetails(ImplicitDict):
    """Information about a flight necessary to plan successfully using the RPAS Platform Operating Rules version 2.6."""

    operator_type: Optional[RPAS26FlightDetailsOperatorType]
    """The type of operator."""

    uas_serial_numbers: Optional[List[str]]
    """The list of UAS/drone serial numbers that will be operated during the operation."""

    uas_registration_numbers: Optional[List[str]]
    """The list of UAS/drone registration numbers that will be operated during the operation."""

    aircraft_type: Optional[RPAS26FlightDetailsAircraftType]
    """Type of vehicle being used as per ASTM F3411-22a."""

    flight_profile: Optional[RPAS26FlightDetailsFlightProfile]
    """Type of flight profile."""

    pilot_license_number: Optional[str]
    """License number for the pilot."""

    pilot_phone_number: Optional[str]
    """Contact phone number for the pilot."""

    operator_number: Optional[str]
    """Operator number."""


# ===== General flight information =====


FlightID = str


class AirspaceUsageState(str, Enum):
    """User's current usage of the airspace defined in the flight plan."""

    Planned = "Planned"
    """The user intends to fly according to this flight plan, but is not currently using the defined area with an active UAS."""

    InUse = "InUse"
    """The user is currently using the defined area with an active UAS."""


class UasState(str, Enum):
    """State of the user's UAS associated with a flight plan."""

    Nominal = "Nominal"
    """The user or UAS reports or implies that it is performing nominally."""

    OffNominal = "OffNominal"
    """The user or UAS reports or implies that it is temporarily not performing nominally, but expects to be able to recover to normal operation."""

    Contingent = "Contingent"
    """The user or UAS reports or implies that it is not performing nominally and may be unable to recover to normal operation."""


class BasicFlightPlanInformation(ImplicitDict):
    """Basic information about a flight plan that an operator and/or UAS can be expected to provide in most flight planning scenarios."""

    usage_state: AirspaceUsageState
    """User's current usage of the airspace specified in the flight plan."""

    uas_state: UasState
    """State of the user's UAS associated with this flight plan."""

    area: List[Volume4D]
    """User intends to or may fly anywhere in this entire area."""


class FlightInfo(ImplicitDict):
    """Details of user's intent to create or modify a flight plan."""

    basic_information: BasicFlightPlanInformation

    astm_f3548_21: Optional[ASTMF354821OpIntentInformation]

    uspace_flight_authorisation: Optional[FlightAuthorisationData]

    rpas_operating_rules_2_6: Optional[RPAS26FlightDetails]

    additional_information: Optional[dict]
    """Any information relevant to a particular jurisdiction or use case not described in the standard schema. The keys and values must be agreed upon between the test designers and USSs under test."""

    @staticmethod
    def from_scd_inject_flight_request(
        request: scd_api.InjectFlightRequest,
    ) -> FlightInfo:
        usage_states = {
            scd_api.OperationalIntentState.Accepted: AirspaceUsageState.Planned,
            scd_api.OperationalIntentState.Activated: AirspaceUsageState.InUse,
            scd_api.OperationalIntentState.Nonconforming: AirspaceUsageState.InUse,
            scd_api.OperationalIntentState.Contingent: AirspaceUsageState.InUse,
        }
        uas_states = {
            scd_api.OperationalIntentState.Accepted: UasState.Nominal,
            scd_api.OperationalIntentState.Activated: UasState.Nominal,
            scd_api.OperationalIntentState.Nonconforming: UasState.OffNominal,
            scd_api.OperationalIntentState.Contingent: UasState.Contingent,
        }
        if (
            request.operational_intent.state
            in (
                scd_api.OperationalIntentState.Accepted,
                scd_api.OperationalIntentState.Activated,
            )
            and request.operational_intent.off_nominal_volumes
        ):
            # This invalid request can no longer be represented with a standard flight planning request
            raise ValueError(
                f"Request for nominal {request.operational_intent.state} operational intent is invalid because it contains off-nominal volumes"
            )
        v4c = Volume4DCollection.from_interuss_scd_api(
            request.operational_intent.volumes
        ) + Volume4DCollection.from_interuss_scd_api(
            request.operational_intent.off_nominal_volumes
        )
        basic_information = BasicFlightPlanInformation(
            usage_state=usage_states[request.operational_intent.state],
            uas_state=uas_states[request.operational_intent.state],
            area=v4c.volumes,
        )
        astm_f3548v21 = ASTMF354821OpIntentInformation(
            priority=request.operational_intent.priority
        )
        uspace_flight_authorisation = ImplicitDict.parse(
            request.flight_authorisation, FlightAuthorisationData
        )
        flight_info = FlightInfo(
            basic_information=basic_information,
            astm_f3548_21=astm_f3548v21,
            uspace_flight_authorisation=uspace_flight_authorisation,
        )
        return flight_info


class ExecutionStyle(str, Enum):
    Hypothetical = "Hypothetical"
    """The user does not want the USS to actually perform any action regarding the actual flight plan. Instead, the user would like to know the likely outcome if the action were hypothetically attempted. The response to this request will not refer to an actual flight plan, or an actual state change in an existing flight plan, but rather a hypothetical flight plan or a hypothetical change to an existing flight plan."""

    IfAllowed = "IfAllowed"
    """The user would like to perform the requested action if it is allowed. If the requested action is allowed, the USS should actually perform the action (e.g., actually create a new ASTM F3548-21 operational intent). If the requested action is not allowed, the USS should indicate that the action is Rejected and not perform the action. The response to this request will refer to an actual flight plan when appropriate, and never refer to a hypothetical flight plan or status."""

    InReality = "InReality"
    """The user is communicating an actual state of reality. The USS should consider the user to be actually performing (or attempting to perform) this action, regardless of whether or not the action is allowed under relevant UTM rules."""
