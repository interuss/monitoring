import datetime
from arrow import ParserError
from implicitdict import StringBasedDateTime
from typing import List, Optional
import s2sphere

from uas_standards.interuss.automated_testing.rid.v1.observation import (
    GetDetailsResponse,
    OperatorAltitudeAltitudeType,
)

from uas_standards.ansi_cta_2063_a import SerialNumber
from uas_standards.astm.f3411 import v22a
from monitoring.monitorlib.fetch.rid import (
    FetchedFlights,
    FlightDetails,
)
from monitoring.monitorlib.geo import validate_lat, validate_lng, Altitude, LatLngPoint
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType, PendingCheck
from monitoring.monitorlib.fetch.rid import Flight, Position


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

        if self._rid_version == RIDVersion.f3411_22a:
            for f in observed_flights.flights:
                # Evaluate on all flights regardless of where they came from
                self._evaluate_operational_status(
                    f.v22a_value.get("current_state", {}).get("operational_status"),
                    participants,
                )
        for f in observed_flights.flights:
            self._evaluate_operational_status(
                f.raw.get("current_state", {}).get("operational_status"),
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
        self._evaluate_operator_id(details.operator_id, participants)
        self._evaluate_operator_location(
            details.operator_location.position,
            details.operator_location.get("altitude"),
            details.operator_location.get("altitude_type"),
            participants,
        )

    def evaluate_dp_details(
        self, observed_details: Optional[GetDetailsResponse], participants: List[str]
    ):
        if not observed_details:
            observed_details = {}

        self._evaluate_plain_uas_id(
            observed_details.get("uas", {}).get("id"), participants
        )

        operator = observed_details.get("operator", {})
        self._evaluate_operator_id(operator.get("id"), participants)

        operator_location = operator.get("location", {})
        operator_altitude = operator.get("altitude", {})
        operator_altitude_value = operator_altitude.get("altitude")
        self._evaluate_operator_location(
            operator_location,
            Altitude.w84m(value=operator_altitude_value)
            if operator_altitude_value
            else None,
            operator_altitude.get("altitude_type"),
            participants,
        )

    def _evaluate_uas_id(
        self, value: Optional[v22a.api.UASID], participants: List[str]
    ):
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
                            participants=participants,
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

    def _evaluate_plain_uas_id(self, value: str, participants: List[str]):
        with self._test_scenario.check(
            "UAS ID presence in flight details", participants
        ) as check:
            if not value:
                check.record_failed(
                    f"UAS ID not present as required by the Common Dictionary definition: {value}",
                    severity=Severity.Medium,
                )
                return

        if SerialNumber(value).valid:
            self._test_scenario.check(
                "UAS ID (Serial Number format) consistency with Common Dictionary",
                participants,
            ).record_passed(participants)

        # TODO: Add registration id format check
        # TODO: Add utm id format check
        # TODO: Add specific session id format check
        # TODO: Add a check to validate at least one format is correct

    def evaluate_timestamp(self, timestamp: str, participants: List[str]):
        with self._test_scenario.check(
                "Timestamp consistency with Common Dictionary", participants
        ) as check:
            try:
                t = StringBasedDateTime(timestamp)
                if t.datetime.utcoffset().seconds != 0:
                    check.record_failed(
                        f"Timestamp must be relative to UTC: {timestamp}",
                        severity=Severity.Medium,
                    )
                deci_seconds = t.datetime.microsecond / 100000
                if deci_seconds - int(deci_seconds) > 0:
                    check.record_failed(
                        f"Timestamp resolution is smaller than 1/10: {timestamp}",
                        severity=Severity.Medium,
                    )
            except ParserError as e:
                check.record_failed(
                    f"Unable to parse timestamp: {timestamp}",
                    details=f"Reason:  {e}",
                    severity=Severity.Medium,
                )

    def _evaluate_operator_id(self, value: Optional[str], participants: List[str]):
        if self._rid_version == RIDVersion.f3411_22a:
            if value:
                with self._test_scenario.check(
                    "Operator ID consistency with Common Dictionary", participants
                ) as check:
                    is_ascii = all([0 <= ord(c) < 128 for c in value])
                    if not is_ascii:
                        check.record_failed(
                            "Operator ID contains non-ascii characters",
                            severity=Severity.Medium,
                        )
        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping Operator ID evaluation",
            )

    def _evaluate_operator_location(
        self,
        position: Optional[LatLngPoint],
        altitude: Optional[Altitude],
        altitude_type: Optional[OperatorAltitudeAltitudeType],
        participants: List[str],
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            with self._test_scenario.check(
                "Operator Location consistency with Common Dictionary", participants
            ) as check:
                if not position:
                    check.record_failed(
                        "Missing Operator position",
                        details=f"Invalid position: {position}",
                        severity=Severity.Medium,
                    )
                    return

                lat = position.lat
                try:
                    lat = validate_lat(lat)
                except ValueError:
                    check.record_failed(
                        "Operator Location contains an invalid latitude",
                        details=f"Invalid latitude: {lat}",
                        severity=Severity.Medium,
                    )
                lng = position.lng
                try:
                    lng = validate_lng(lng)
                except ValueError:
                    check.record_failed(
                        "Operator Location contains an invalid longitude",
                        details=f"Invalid longitude: {lng}",
                        severity=Severity.Medium,
                    )

            alt = altitude
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
                    if alt.value != round(alt.value):
                        check.record_failed(
                            "Operator Altitude must have a minimum resolution of 1 m.",
                            details=f"Invalid Operator Altitude: {alt.value}",
                            severity=Severity.Medium,
                        )

                alt_type = altitude_type
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

        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping Operator Location evaluation",
            )

    def _evaluate_operational_status(
        self, value: Optional[str], participants: List[str]
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            if value:
                with self._test_scenario.check(
                    "Operational Status consistency with Common Dictionary",
                    participants,
                ) as check:
                    try:
                        v22a.api.RIDOperationalStatus(value)
                    except ValueError:
                        check.record_failed(
                            "Operational Status is invalid",
                            details=f"Invalid Operational Status: {value}",
                            severity=Severity.Medium,
                        )
        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping Operational Status evaluation",
            )
