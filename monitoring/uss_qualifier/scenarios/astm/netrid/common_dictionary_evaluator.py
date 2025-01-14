import datetime
import math
from typing import List, Optional

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
    RIDAircraftPosition,
)

from monitoring.monitorlib.fetch.rid import (
    FlightDetails,
)
from monitoring.monitorlib.fetch.rid import Flight, Position
from monitoring.monitorlib.geo import validate_lat, validate_lng, Altitude, LatLngPoint
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


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

    def evaluate_sp_flight(
        self,
        injected_flight: injection.TestFlight,
        observed_flight: Flight,
        participant_id: ParticipantID,
        query_timestamp: datetime.datetime,
    ):
        """Implements fragment documented in `common_dictionary_evaluator_sp_flight.md`."""

        self._evaluate_ua_type(
            injected_flight,
            observed_flight,
            None,
            participant_id,
            query_timestamp,
        )

        self._evaluate_operational_status(
            observed_flight.operational_status,
            [participant_id],
        )

    def evaluate_dp_flight(
        self,
        injected_telemetry: injection.RIDAircraftState,
        injected_flight: injection.TestFlight,
        observed_flight: observation_api.Flight,
        participants: List[str],
        query_timestamp: datetime.datetime,
    ):
        """Implements fragment documented in `common_dictionary_evaluator_dp_flight.md`."""

        self._evaluate_ua_type(
            injected_flight,
            None,
            observed_flight,
            participants[
                0
            ],  # TODO: flatten 'participants', it always has a single value
            query_timestamp,
        )

        # If the state is present, we do validate its content,
        # but its presence is optional
        if injected_telemetry.has_field_with_value("current_state"):
            self._evaluate_speed(
                injected_telemetry.speed,
                observed_flight.current_state.speed,
                participants,
            )
            self._evaluate_track(
                injected_telemetry.track,
                observed_flight.current_state.track,
                participants,
            )
            self._evaluate_timestamp(
                injected_telemetry.timestamp,
                observed_flight.current_state.timestamp,
                participants,
            )

            # TODO check if worth adding correctness check here, it requires some slight (possibly non-trivial)
            #  changes in evaluate_sp_flights as well
            self._evaluate_operational_status(
                observed_flight.current_state.operational_status, participants
            )

        self._evaluate_position(
            injected_telemetry.position,
            observed_flight.most_recent_position,
            participants,
        )
        self._evaluate_height(
            injected_telemetry.get("height"),
            observed_flight.most_recent_position.get("height"),
            participants,
        )

    def evaluate_sp_details(self, details: FlightDetails, participants: List[str]):
        """Implements fragment documented in `common_dictionary_evaluator_sp_flight_details.md`."""

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
        """Implements fragment documented in `common_dictionary_evaluator_dp_flight_details.md`."""

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
                    "Height consistency with Common Dictionary", participants
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
                    if not math.isclose(
                        height_obs.distance, height_inj.distance, abs_tol=1.0
                    ):
                        check.record_failed(
                            "Observed Height is inconsistent with injected one",
                            details=f"Observed height: {height_obs} - injected: {height_inj}",
                            severity=Severity.Medium,
                        )

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
                    "Height Type is consistent with injected one", participants
                ) as check:
                    if height_obs.reference != height_inj.reference:
                        check.record_failed(
                            "Observed Height type is inconsistent with injected one",
                            details=f"Observed height: {height_obs} - injected: {height_inj}",
                            severity=Severity.Medium,
                        )
        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping Height and Height Type evaluation",
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

    def _evaluate_ua_type(
        self,
        injected_flight: injection.TestFlight,
        sp_observed_flight: Optional[Flight],
        dp_observed_flight: Optional[observation_api.Flight],
        participant: ParticipantID,
        query_timestamp: datetime.datetime,
    ):
        """
        Evaluates UA type. Exactly one of sp_observed_flight or dp_observed_flight must be provided.
        See as well `common_dictionary_evaluator.md`.

        Args:
            injected_flight: injected flight as returned by the injection API.
            sp_observed_flight: flight observed through the SP API.
            dp_observed_flight: flight observed through the observation API.
            participant: participant providing the API through which the value was observed.
            query_timestamp: timestamp of the observation query.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        injected_val: Optional[injection.UAType] = injected_flight.get("aircraft_type")
        if injected_val is not None:
            try:
                injected_val = injection.UAType(injected_val)
            except ValueError as e:
                raise ValueError(f"Invalid UA type {injected_val} injected", e)

        observed_val: Optional[injection.UAType]
        if sp_observed_flight is not None:
            observed_val = sp_observed_flight.aircraft_type
        elif dp_observed_flight is not None:
            observed_val = dp_observed_flight.get("aircraft_type")
        else:
            raise ValueError("No observed flight provided.")

        with self._test_scenario.check(
            "UA type is exposed correctly",
            participant,
        ) as check:
            if sp_observed_flight is not None:
                if observed_val is None:  # C3
                    check.record_failed(
                        "UA type is missing",
                        details="SP did not return any UA type",
                        query_timestamps=[query_timestamp],
                    )

            if observed_val is not None:  # C5 / C9
                try:
                    injection.UAType(observed_val)
                except ValueError:
                    check.record_failed(
                        "UA type is invalid",
                        details=f"USS returned an invalid UA type: {observed_val}.",
                        query_timestamps=[query_timestamp],
                    )

                if (
                    self._rid_version == RIDVersion.f3411_19
                    and observed_val == injection.UAType.HybridLift
                ) or (
                    self._rid_version == RIDVersion.f3411_22a
                    and observed_val == injection.UAType.VTOL
                ):
                    check.record_failed(
                        "UA type is inconsistent with RID version",
                        details=f"USS returned the UA type {observed_val} which is not supported by the RID version used ({self._rid_version}).",
                        query_timestamps=[query_timestamp],
                    )

        with self._test_scenario.check(
            "UA type is consistent with injected value",
            participant,
        ) as check:
            equivalent = {injection.UAType.HybridLift, injection.UAType.VTOL}

            if injected_val is None:
                if (
                    sp_observed_flight is not None
                    and observed_val != injection.UAType.NotDeclared
                ):  # C6
                    check.record_failed(
                        "UA type is inconsistent, expected 'NotDeclared' since no value was injected",
                        details=f"SP returned the UA type {observed_val}, yet no value was injected, which should have been mapped to 'NotDeclared'.",
                        query_timestamps=[query_timestamp],
                    )

                if dp_observed_flight is not None and observed_val is not None:  # C10
                    check.record_failed(
                        "UA type is inconsistent, expected no value since none was injected",
                        details=f"DP returned the UA type {observed_val}, yet no value was injected.",
                        query_timestamps=[query_timestamp],
                    )

            elif injected_val in equivalent:
                if observed_val not in equivalent:  # C7 / C10
                    check.record_failed(
                        "UA type is inconsistent with injected value",
                        details=f"USS returned the UA type {observed_val}, yet the value {injected_val} was injected, given that {equivalent} are equivalent .",
                        query_timestamps=[query_timestamp],
                    )

            elif injected_val != observed_val:  # C7 / C10
                check.record_failed(
                    "UA type is inconsistent with injected value",
                    details=f"USS returned the UA type {observed_val}, yet the value {injected_val} was injected.",
                    query_timestamps=[query_timestamp],
                )
