import datetime
import math
from typing import List, Optional

import s2sphere
from arrow import ParserError
from implicitdict import StringBasedDateTime
from uas_standards.ansi_cta_2063_a import SerialNumber
from uas_standards.astm.f3411 import v22a
from uas_standards.astm.f3411.v22a.api import UASID
from uas_standards.astm.f3411.v22a.constants import (
    SpecialSpeed,
    MaxSpeed,
    SpecialTrackDirection,
    MinTrackDirection,
    MaxTrackDirection,
)
from uas_standards.interuss.automated_testing.rid.v1 import (
    observation as observation_api,
    injection,
)
from uas_standards.interuss.automated_testing.rid.v1.injection import (
    RIDAircraftState,
    RIDAircraftPosition,
)

from monitoring.monitorlib.fetch.rid import (
    FetchedFlights,
    FlightDetails,
)
from monitoring.monitorlib.fetch.rid import Flight, Position
from monitoring.monitorlib.geo import validate_lat, validate_lng, Altitude, LatLngPoint
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType, PendingCheck

# SP responses to /flights endpoint's p99 should be below this:
SP_FLIGHTS_RESPONSE_TIME_TOLERANCE_SEC = 3
NET_MAX_NEAR_REAL_TIME_DATA_PERIOD_SEC = 60
_POSITION_TIMESTAMP_MAX_AGE_SEC = (
    NET_MAX_NEAR_REAL_TIME_DATA_PERIOD_SEC + SP_FLIGHTS_RESPONSE_TIME_TOLERANCE_SEC
)


class RIDCommonDictionaryEvaluator(object):
    def __init__(
        self,
        config: EvaluationConfiguration,
        test_scenario: TestScenarioType,
        rid_version: RIDVersion,
    ) -> None:
        self._config = config
        self._test_scenario = test_scenario
        self._rid_version = rid_version

    def evaluate_sp_flights(
        self,
        requested_area: s2sphere.LatLngRect,
        observed_flights: FetchedFlights,
        participants: List[str],
    ):
        for url, uss_flights in observed_flights.uss_flight_queries.items():
            # For the timing checks, we want to look at the flights relative to the query
            # they came from, as they may be provided from different SP's.
            for f in uss_flights.flights:
                self.evaluate_sp_flight_recent_positions_times(
                    f,
                    uss_flights.query.response.reported.datetime,
                    participants,
                )

                self.evaluate_sp_flight_recent_positions_crossing_area_boundary(
                    requested_area, f, participants
                )

        for f in observed_flights.flights:
            # Evaluate on all flights regardless of where they came from
            self._evaluate_operational_status(
                f.operational_status,
                participants,
            )

    def evaluate_dp_flight(
        self,
        injected_flight: RIDAircraftState,
        observed_flight: observation_api.Flight,
        participants: List[str],
    ):
        # If the state is present, we do validate its content,
        # but its presence is optional
        if injected_flight.has_field_with_value("current_state"):
            self._evaluate_speed(
                injected_flight.speed, observed_flight.current_state.speed, participants
            )
            self._evaluate_track(
                injected_flight.track, observed_flight.current_state.track, participants
            )
            self._evaluate_timestamp(
                injected_flight.timestamp,
                observed_flight.current_state.timestamp,
                participants,
            )

            # TODO check if worth adding correctness check here, it requires some slight (possibly non-trivial)
            #  changes in evaluate_sp_flights as well
            self._evaluate_operational_status(
                observed_flight.current_state.operational_status, participants
            )

        self._evaluate_position(
            injected_flight.position, observed_flight.most_recent_position, participants
        )
        self._evaluate_height(
            injected_flight.get("height"),
            observed_flight.most_recent_position.get("height"),
            participants,
        )

    def _evaluate_recent_position_time(
        self, p: Position, query_time: datetime.datetime, check: PendingCheck
    ):
        """Check that the position's timestamp is at most 60 seconds before the request time."""
        if (query_time - p.time).total_seconds() > _POSITION_TIMESTAMP_MAX_AGE_SEC:
            check.record_failed(
                "A Position timestamp was older than the tolerance.",
                details=f"Position timestamp: {p.time}, query time: {query_time}",
                severity=Severity.Medium,
            )

    def evaluate_sp_flight_recent_positions_times(
        self, f: Flight, query_time: datetime.datetime, participants: List[str]
    ):
        with self._test_scenario.check(
            "Recent positions timestamps", participants
        ) as check:
            for p in f.recent_positions:
                self._evaluate_recent_position_time(p, query_time, check)

    def _chronological_positions(self, f: Flight) -> List[s2sphere.LatLng]:
        """
        Returns the recent positions of the flight, ordered by time with the oldest first, and the most recent last.
        """
        return [
            s2sphere.LatLng.from_degrees(p.lat, p.lng)
            for p in sorted(f.recent_positions, key=lambda p: p.time)
        ]

    def _sliding_triples(
        self, points: List[s2sphere.LatLng]
    ) -> List[List[s2sphere.LatLng]]:
        """
        Returns a list of triples of consecutive positions in passed the list.
        """
        return [
            (points[i], points[i + 1], points[i + 2]) for i in range(len(points) - 2)
        ]

    def evaluate_sp_flight_recent_positions_crossing_area_boundary(
        self, requested_area: s2sphere.LatLngRect, f: Flight, participants: List[str]
    ):
        with self._test_scenario.check(
            "Recent positions for aircraft crossing the requested area boundary show only one position before or after crossing",
            participants,
        ) as check:

            def fail_check():
                check.record_failed(
                    "A position outside the area was neither preceded nor followed by a position inside the area.",
                    details=f"Positions: {f.recent_positions}, requested_area: {requested_area}",
                    severity=Severity.Medium,
                )

            positions = self._chronological_positions(f)
            if len(positions) < 2:
                # Check does not apply in this case
                return

            if len(positions) == 2:
                # Only one of the positions can be outside the area. If both are, we fail.
                if not requested_area.contains(
                    positions[0]
                ) and not requested_area.contains(positions[1]):
                    fail_check()
                return

            # For each sliding triple we check that if the middle position is outside the area, then either
            # the first or the last position is inside the area. This means checking for any point that is inside the
            # area in the triple and failing otherwise
            for triple in self._sliding_triples(self._chronological_positions(f)):
                if not (
                    requested_area.contains(triple[0])
                    or requested_area.contains(triple[1])
                    or requested_area.contains(triple[2])
                ):
                    fail_check()

            # Finally we need to check for the forbidden corner cases of having the two first or two last positions being outside.
            # (These won't be caught by the iteration on the triples above)
            if (
                not requested_area.contains(positions[0])
                and not requested_area.contains(positions[1])
            ) or (
                not requested_area.contains(positions[-1])
                and not requested_area.contains(positions[-2])
            ):
                fail_check()

    def evaluate_sp_details(self, details: FlightDetails, participants: List[str]):
        self._evaluate_uas_id(details.raw.get("uas_id"), participants)
        self._evaluate_operator_id(None, details.operator_id, participants)
        self._evaluate_operator_location(
            None,
            None,
            None,
            details.operator_location,
            details.operator_altitude,
            details.operator_altitude_type,
            participants,
        )

    def evaluate_dp_details(
        self,
        injected_details: injection.RIDFlightDetails,
        observed_details: Optional[observation_api.GetDetailsResponse],
        participants: List[str],
    ):
        if not observed_details:
            return

        self._evaluate_arbitrary_uas_id(
            injected_details.get(
                "uas_id", injected_details.get("serial_number", None)
            ),  # fall back on seria number if no UAS ID
            observed_details.get("uas", {}).get("id", None),
            participants,
        )

        operator_obs = observed_details.get("operator", {})

        self._evaluate_operator_id(
            injected_details.operator_id, operator_obs.get("id", None), participants
        )

        operator_altitude_obs = operator_obs.get("altitude", {})
        operator_altitude_value_obs = operator_altitude_obs.get("altitude")
        operator_altitude_inj = injected_details.get("operator_altitude", {})
        self._evaluate_operator_location(
            injected_details.get("operator_location", None),
            operator_altitude_inj.get(
                "altitude", None
            ),  # should be of the correct type already
            operator_altitude_inj.get("altitude_type", None),
            operator_obs.get("location", None),
            Altitude.w84m(value=operator_altitude_value_obs),
            operator_altitude_obs.get("altitude_type", None),
            participants,
        )

    def _evaluate_uas_id(self, value: Optional[UASID], participants: List[str]):
        if self._rid_version == RIDVersion.f3411_22a:
            formats_keys = [
                "serial_number",
                "registration_id",
                "utm_id",
                "specific_session_id",
            ]
            formats_count = (
                0
                if value is None
                else sum([0 if value.get(v) is None else 1 for v in formats_keys])
            )
            with self._test_scenario.check(
                "UAS ID presence in flight details", participants
            ) as check:
                if formats_count == 0:
                    check.record_failed(
                        f"UAS ID not present as required by the Common Dictionary definition: {value}",
                        severity=Severity.Medium,
                    )
                    return

            serial_number = value.get("serial_number")
            if serial_number:
                with self._test_scenario.check(
                    "UAS ID (Serial Number format) consistency with Common Dictionary",
                    participants,
                ) as check:
                    if not SerialNumber(serial_number).valid:
                        check.record_failed(
                            f"Invalid uas_id serial number: {serial_number}",
                            severity=Severity.Medium,
                        )
                    else:
                        check.record_passed()

            # TODO: Add registration id format check
            # TODO: Add utm id format check
            # TODO: Add specific session id format check
        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping UAS ID evaluation",
            )

    def _evaluate_arbitrary_uas_id(
        self, value_inj: str, value_obs: str, participants: List[str]
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            with self._test_scenario.check(
                "UAS ID presence in flight details", participants
            ) as check:
                if value_obs is None:
                    check.record_failed(
                        f"UAS ID not present as required by the Common Dictionary definition: {value_obs}",
                        severity=Severity.Medium,
                    )
                    return

            if SerialNumber(value_obs).valid:
                self._test_scenario.check(
                    "UAS ID (Serial Number format) consistency with Common Dictionary",
                    participants,
                ).record_passed()

            if value_obs is not None:
                with self._test_scenario.check(
                    "UAS ID is consistent with injected one", participants
                ) as check:
                    if value_inj != value_obs:
                        check.record_failed(
                            "Observed UAS ID not consistent with injected one",
                            details=f"Observed: {value_obs} - injected: {value_inj}",
                            severity=Severity.Medium,
                        )

        # TODO: Add registration id format check
        # TODO: Add utm id format check
        # TODO: Add specific session id format check
        # TODO: Add a check to validate at least one format is correct
        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping arbitrary uas id evaluation",
            )

    def _evaluate_timestamp(
        self, timestamp_inj: str, timestamp_obs: Optional[str], participants: List[str]
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            with self._test_scenario.check(
                "Timestamp consistency with Common Dictionary", participants
            ) as check:
                if timestamp_obs is None:
                    check.record_failed(
                        f"Timestamp not present",
                        details=f"The timestamp must be specified.",
                        severity=Severity.High,
                    )

                try:
                    t_obs = StringBasedDateTime(timestamp_obs)
                    if t_obs.datetime.utcoffset().seconds != 0:
                        check.record_failed(
                            f"Timestamp must be relative to UTC: {t_obs}",
                            severity=Severity.Medium,
                        )
                except ParserError as e:
                    check.record_failed(
                        f"Unable to parse timestamp: {timestamp_obs}",
                        details=f"Reason:  {e}",
                        severity=Severity.Medium,
                    )

            if timestamp_obs:
                with self._test_scenario.check(
                    "Observed timestamp is consistent with injected one", participants
                ) as check:
                    t_inj = StringBasedDateTime(timestamp_inj)
                    if abs(t_inj.datetime - t_obs.datetime).total_seconds() > 1.0:
                        check.record_failed(
                            "Observed timestamp inconsistent with injected one",
                            details=f"Injected timestamp: {timestamp_inj} - Observed one: {timestamp_obs}",
                            severity=Severity.Medium,
                        )
        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping timestamp evaluation",
            )

    def _evaluate_operator_id(
        self,
        value_inj: Optional[str],
        value_obs: Optional[str],
        participants: List[str],
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            if value_obs:
                with self._test_scenario.check(
                    "Operator ID consistency with Common Dictionary", participants
                ) as check:
                    is_ascii = all([0 <= ord(c) < 128 for c in value_obs])
                    if not is_ascii:
                        check.record_failed(
                            "Operator ID contains non-ascii characters",
                            severity=Severity.Medium,
                        )

            if value_inj is not None:
                with self._test_scenario.check(
                    "Operator ID is consistent with injected one", participants
                ) as check:
                    if value_inj != value_obs:
                        check.record_failed(
                            "Observed Operator ID not consistent with injected one",
                            details=f"Observed: {value_obs} - injected: {value_inj}",
                            severity=Severity.Medium,
                        )

        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping operator id evaluation",
            )

    def _evaluate_speed(
        self, speed_inj: float, speed_obs: Optional[float], participants: List[str]
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            with self._test_scenario.check(
                "Speed consistency with Common Dictionary", participants
            ) as check:
                if speed_obs is None:
                    check.record_failed(
                        f"Speed not present",
                        details=f"The speed must be specified.",
                        severity=Severity.High,
                    )

                if not (
                    0 <= speed_obs <= MaxSpeed or math.isclose(speed_obs, SpecialSpeed)
                ):
                    check.record_failed(
                        f"Invalid speed: {speed_obs}",
                        details=f"The speed shall be greater than 0 and less than {MaxSpeed}. The Special Value {SpecialSpeed} is allowed.",
                        severity=Severity.Medium,
                    )

            if speed_obs is not None:
                with self._test_scenario.check(
                    "Observed speed is consistent with injected one", participants
                ) as check:
                    # Speed seems rounded to nearest 0.25 m/s -> x.0, x.25, x.5, x.75, (x+1).0
                    if abs(speed_obs - speed_inj) > 0.125:
                        check.record_failed(
                            "Observed speed different from injected speed",
                            details=f"Injected speed was {speed_inj} - observed speed is {speed_obs}",
                            severity=Severity.Medium,
                        )
        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping speed evaluation",
            )

    def _evaluate_track(
        self, track_inj: float, track_obs: Optional[float], participants: List[str]
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            with self._test_scenario.check(
                "Track Direction consistency with Common Dictionary", participants
            ) as check:
                if track_obs is None:
                    check.record_failed(
                        f"Track direction not present",
                        details=f"The track direction must be specified.",
                        severity=Severity.High,
                    )

                if not (
                    MinTrackDirection <= track_obs <= MaxTrackDirection
                    or round(track_obs) == SpecialTrackDirection
                ):
                    check.record_failed(
                        f"Invalid track direction: {track_obs}",
                        details=f"The track direction shall be greater than -360 and less than {MaxSpeed}. The Special Value {SpecialSpeed} is allowed.",
                        severity=Severity.Medium,
                    )

            if track_obs is not None:
                with self._test_scenario.check(
                    "Observed track is consistent with injected one", participants
                ) as check:
                    # Track seems rounded to nearest integer.
                    abs_track_diff = min(
                        (track_inj - track_obs) % 360, (track_obs - track_inj) % 360
                    )
                    if abs_track_diff > 0.5:
                        check.record_failed(
                            "Observed track direction different from injected one",
                            details=f"Inject track was {track_inj} - observed one is {track_obs}",
                            severity=Severity.Medium,
                        )

        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping track direction evaluation",
            )

    def _evaluate_position(
        self,
        position_inj: RIDAircraftPosition,
        position_obs: Position,
        participants: List[str],
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            with self._test_scenario.check(
                "Current Position consistency with Common Dictionary", participants
            ) as check:
                lat = position_obs.lat
                try:
                    lat = validate_lat(lat)
                except ValueError:
                    check.record_failed(
                        "Current Position contains an invalid latitude",
                        details=f"Invalid latitude: {lat}",
                        severity=Severity.Medium,
                    )
                lng = position_obs.lng
                try:
                    lng = validate_lng(lng)
                except ValueError:
                    check.record_failed(
                        "Current Position contains an invalid longitude",
                        details=f"Invalid longitude: {lng}",
                        severity=Severity.Medium,
                    )
            with self._test_scenario.check(
                "Observed Position is consistent with injected one", participants
            ) as check:
                # TODO is this too lax?
                if (
                    abs(position_inj.lat - position_obs.lat) > 0.01
                    or abs(position_inj.lng - position_obs.lng) > 0.01
                ):
                    check.record_failed(
                        "Observed position inconsistent with injected one",
                        details=f"Injected Position: {position_inj} - Observed Position: {position_obs}",
                        severity=Severity.Medium,
                    )
        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping position evaluation",
            )

    def _evaluate_height(
        self,
        height_inj: Optional[injection.RIDHeight],
        height_obs: Optional[observation_api.RIDHeight],
        participants: List[str],
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            if height_obs is not None:
                with self._test_scenario.check(
                    "Height Type consistency with Common Dictionary", participants
                ) as check:
                    if (
                        height_obs.reference
                        != observation_api.RIDHeightReference.TakeoffLocation
                        and height_obs.reference
                        != observation_api.RIDHeightReference.GroundLevel
                    ):
                        check.record_failed(
                            f"Invalid height type: {height_obs.reference}",
                            details=f"The height type reference shall be either {observation_api.RIDHeightReference.TakeoffLocation} or {observation_api.RIDHeightReference.GroundLevel}",
                            severity=Severity.Medium,
                        )

                with self._test_scenario.check(
                    "Height is consistent with injected one", participants
                ) as check:
                    if (
                        height_obs.reference != height_inj.reference
                        or abs(height_obs.distance - height_inj.distance) > 1.0
                    ):
                        check.record_failed(
                            "Observed Height is inconsistent with injected one",
                            details=f"Observed height: {height_obs} - injected: {height_inj}",
                            severity=Severity.Medium,
                        )
        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping Height evaluation",
            )

    def _evaluate_operator_location(
        self,
        position_inj: Optional[LatLngPoint],
        altitude_inj: Optional[Altitude],
        altitude_type_inj: Optional[injection.OperatorAltitudeAltitudeType],
        position_obs: Optional[LatLngPoint],
        altitude_obs: Optional[Altitude],
        altitude_type_obs: Optional[observation_api.OperatorAltitudeAltitudeType],
        participants: List[str],
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            if not position_obs:
                return  # Operator location is optional and there was no location specified

            with self._test_scenario.check(
                "Operator Location consistency with Common Dictionary", participants
            ) as check:
                lat = position_obs.lat
                try:
                    lat = validate_lat(lat)
                except ValueError:
                    check.record_failed(
                        "Operator Location contains an invalid latitude",
                        details=f"Invalid latitude: {lat}",
                        severity=Severity.Medium,
                    )
                lng = position_obs.lng
                try:
                    lng = validate_lng(lng)
                    position_valid = True
                except ValueError:
                    position_valid = False
                    check.record_failed(
                        "Operator Location contains an invalid longitude",
                        details=f"Invalid longitude: {lng}",
                        severity=Severity.Medium,
                    )

            if position_valid and position_obs is not None and position_inj is not None:
                with self._test_scenario.check(
                    "Operator Location is consistent with injected one", participants
                ) as check:
                    if (
                        abs(position_obs.lat - position_inj.lat) > 0.01
                        or abs(position_obs.lng - position_obs.lng) > 0.01
                    ):
                        check.record_failed(
                            summary="Operator Location not consistent with injected one",
                            details=f"Observed: {position_obs} - injected: {position_inj}",
                            severity=Severity.Medium,
                        )

            alt = altitude_obs
            if alt:
                with self._test_scenario.check(
                    "Operator Altitude consistency with Common Dictionary",
                    participants,
                ) as check:
                    if alt.reference != v22a.api.AltitudeReference.W84:
                        check.record_failed(
                            "Operator Altitude shall be based on WGS-84 height above ellipsoid (HAE)",
                            details=f"Invalid Operator Altitude reference: {alt.reference}",
                            severity=Severity.Medium,
                        )
                    if alt.units != v22a.api.AltitudeUnits.M:
                        check.record_failed(
                            "Operator Altitude units shall be provided in meters",
                            details=f"Invalid Operator Altitude units: {alt.units}",
                            severity=Severity.Medium,
                        )
                if altitude_inj is not None:

                    with self._test_scenario.check(
                        "Operator Altitude is consistent with injected one",
                        participants,
                    ) as check:
                        if (
                            alt.units != altitude_inj.units
                            or alt.reference != altitude_inj.reference
                            or abs(alt.value - altitude_inj.value) > 1
                        ):
                            check.record_failed(
                                "Observed operator altitude inconsistent with injected one",
                                details=f"Observed: {alt} - injected: {altitude_inj}",
                                severity=Severity.Medium,
                            )

                alt_type = altitude_type_obs
                if alt_type:
                    with self._test_scenario.check(
                        "Operator Altitude Type consistency with Common Dictionary",
                        participants,
                    ) as check:
                        try:
                            v22a.api.OperatorLocationAltitudeType(
                                alt_type
                            )  # raise ValueError if alt_type is invalid
                        except ValueError:
                            check.record_failed(
                                "Operator Location contains an altitude type which is invalid",
                                details=f"Invalid altitude type: {alt_type}",
                                severity=Severity.Medium,
                            )

                    if altitude_type_inj is not None:
                        with self._test_scenario.check(
                            "Operator Altitude Type is consistent with injected one",
                            participants,
                        ) as check:
                            if alt_type != altitude_type_inj:
                                check.record_failed(
                                    "Observed Operator Altitude Type is inconsistent with injected one",
                                    details=f"Observed: {alt_type} - Injected: {altitude_type_inj}",
                                    severity=Severity.Medium,
                                )

        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping Operator Location evaluation",
            )

    def _evaluate_operational_status(
        self,
        value_obs: Optional[str],
        participants: List[str],
        value_inj: Optional[str] = None,
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            if value_obs is not None:
                with self._test_scenario.check(
                    "Operational Status consistency with Common Dictionary",
                    participants,
                ) as check:
                    try:
                        v22a.api.RIDOperationalStatus(value_obs)
                    except ValueError:
                        check.record_failed(
                            "Operational Status is invalid",
                            details=f"Invalid Operational Status: {value_obs}",
                            severity=Severity.Medium,
                        )
                # We only check if an injected value: when SP values are evaluated we don't compare with the injected
                # value, for example.
                if value_inj is not None:
                    with self._test_scenario.check(
                        "Operational Status is consistent with injected one",
                        participants,
                    ) as check:
                        if not value_obs == value_inj:
                            check.record_failed(
                                "Observed operational status inconsistent with injected one",
                                severity=Severity.Medium,
                                details=f"Injected operational status: {value_inj} - Observed {value_obs}",
                            )

        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping Operational Status evaluation",
            )
