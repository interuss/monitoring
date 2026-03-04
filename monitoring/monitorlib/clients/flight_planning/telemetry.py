from enum import Enum

from implicitdict import ImplicitDict

from monitoring.monitorlib.geo import Altitude, LatLngPoint
from monitoring.monitorlib.temporal import Time


class HorizontalAccuracy(str, Enum):
    """This is the NACp enumeration from ADS-B, plus 1m for a more complete range for UAs."""

    HAUnknown = "HAUnknown"
    HA10NMPlus = "HA10NMPlus"
    HA10NM = "HA10NM"
    HA4NM = "HA4NM"
    HA2NM = "HA2NM"
    HA1NM = "HA1NM"
    HA05NM = "HA05NM"
    HA03NM = "HA03NM"
    HA01NM = "HA01NM"
    HA005NM = "HA005NM"
    HA30m = "HA30m"
    HA10m = "HA10m"
    HA3m = "HA3m"
    HA1m = "HA1m"


class VerticalAccuracy(str, Enum):
    """This is the GVA enumeration from ADS-B, plus some finer values for UAs."""

    VAUnknown = "VAUnknown"
    VA150mPlus = "VA150mPlus"
    VA150m = "VA150m"
    VA45m = "VA45m"
    VA25m = "VA25m"
    VA10m = "VA10m"
    VA3m = "VA3m"
    VA1m = "VA1m"


class SpeedAccuracy(str, Enum):
    """This is the same enumeration scale and values from ADS-B NACv."""

    SAUnknown = "SAUnknown"
    SA10mpsPlus = "SA10mpsPlus"
    SA10mps = "SA10mps"
    SA3mps = "SA3mps"
    SA1mps = "SA1mps"
    SA03mps = "SA03mps"


class OperationalStatus(str, Enum):
    """Indicates operational status of associated aircraft.
    * `Undeclared`: The system does not support acquisition of knowledge about the status of the aircraft.
    * `Ground`: The aircraft is reporting status but is not airborne.
    * `Airborne`: The aircraft is, or should be considered as, being airborne.
    * `Emergency`: The aircraft is reporting an emergency.
    * `SystemFailure`: Some aspect of the reporting/telemetry system has failed, but the aircraft is not in emergency.
    * `Unknown`: The system supports acquisition of knowledge about the status of the aircraft, but the status cannot currently be determined.
    """

    Undeclared = "Undeclared"
    Ground = "Ground"
    Airborne = "Airborne"
    Emergency = "Emergency"
    SystemFailure = "SystemFailure"
    Unknown = "Unknown"


class FunctionalState(str, Enum):
    """Functional state of the user's UAS associated with this flight plan.

    - `Nominal`: The user or UAS reports or implies that it is performing nominally, or has not indicated
      `OffNominal` or `Contingent`.

    - `OffNominal`: The user or UAS reports or implies that it is temporarily not performing nominally, but
      may expect to be able to recover to normal operation.

    - `Contingent`: The user or UAS reports or implies that it is not performing nominally and may be unable
      to recover to normal operation.

    - `NotSpecified`: The UAS status is not currently available or known (for instance, if the flight is
      planned in the future and the UAS that will be flying has not yet connected to the system).
    """

    Nominal = "Nominal"
    OffNominal = "OffNominal"
    Contingent = "Contingent"
    NotSpecified = "NotSpecified"


class AircraftPosition(ImplicitDict):
    """Reported or actual position of an aircraft at a particular time."""

    location: LatLngPoint | None

    altitudes: list[Altitude] | None
    """The single vertical location of the aircraft, potentially reported relative to multiple datums."""

    accuracy_h: HorizontalAccuracy | None
    """Horizontal error that may be be present in this reported position."""

    accuracy_v: VerticalAccuracy | None
    """Vertical error that may be present in this reported position."""

    pressure_altitude: float | None = 0.0
    """The uncorrected altitude (based on reference standard 29.92 inHg, 1013.25 mb) provides a reference for algorithms that utilize "altitude deltas" between aircraft.  This value is provided in meters."""


class AircraftState(ImplicitDict):
    """State of an aircraft for the purposes of simulating the execution of a flight plan."""

    id: str
    """Unique identifier for this aircraft state/telemetry.  The content of an AircraftState with a given ID must not change over time.  Therefore, if a USS has already queued an aircraft state with this ID as telemetry to be delivered, this state may be ignored."""

    timestamp: Time
    """Time at which this state is valid.  This is equivalent to the time of sensor measurement, so the USS's primary system under test should not be aware of this state until after this time."""

    timestamp_accuracy: float | None = 0.0
    """Declaration of timestamp accuracy, which is the one-sided width of the 95%-confidence interval around `timestamp` for the true time of applicability for any of the data fields."""

    position: AircraftPosition | None

    operational_status: OperationalStatus | None

    uas_state: FunctionalState | None
    """State of the user's UAS associated with this flight plan as reported by the operator.  If the UAS reports its own state, that report will be reflected here.  If the operator reports the UAS state, that report will be reflected in the BasicFlightPlanInformation.
    If a system accepts UAS state reports from both the operator and UAS, it is possible the reported state may differ between those two sources.
    """

    track: float | None = 0.0
    """Direction of flight expressed as a "True North-based" ground track angle.  This value is provided in degrees East of North.  A value of 360 indicates that the true value is unavailable."""

    speed: float | None = 0.0
    """Ground speed of flight in meters per second."""

    speed_accuracy: SpeedAccuracy | None
    """Accuracy of horizontal ground speed."""

    vertical_speed: float | None = 0.0
    """Geodetic vertical speed upward.  Units of meters per second."""


class FlightTelemetry(ImplicitDict):
    """When this information is present and the USS supports telemetry ingestion for a flight, the USS receiving this information should enqueue these telemetry reports to be delivered to the system, as if they were coming from the user, at (or soon after) the specified times."""

    states: list[AircraftState] | None = []
    """The set of telemetry data that should be injected into the system (as if reported by the user or the user's system) at the appropriate times (and not before) for this flight."""
