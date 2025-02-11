import datetime
import math
from collections.abc import Callable
from typing import Any, List, Optional, TypeVar, Union

from arrow import ParserError
from implicitdict import StringBasedDateTime
from uas_standards.ansi_cta_2063_a import SerialNumber
from uas_standards.astm.f3411 import v22a
from uas_standards.astm.f3411.v22a import constants
from uas_standards.astm.f3411.v22a.api import (
    UASID,
    HorizontalAccuracy,
    SpeedAccuracy,
    UAClassificationEUCategory,
    UAClassificationEUClass,
    VerticalAccuracy,
)
from uas_standards.interuss.automated_testing.rid.v1 import injection
from uas_standards.interuss.automated_testing.rid.v1 import (
    observation as observation_api,
)
from uas_standards.interuss.automated_testing.rid.v1.injection import (
    RIDAircraftPosition,
)

from monitoring.monitorlib.fetch.rid import Flight, FlightDetails, Position
from monitoring.monitorlib.geo import (
    DISTANCE_TOLERANCE_M,
    Altitude,
    LatLngPoint,
    validate_lat,
    validate_lng,
)
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.scenarios.scenario import PendingCheck, TestScenarioType

T = TypeVar("T")


class RIDCommonDictionaryEvaluator(object):

    flight_evaluators = [
        "_evaluate_ua_type",
    ]
    telemetry_evaluators = [
        "_evaluate_timestamp_accuracy",
        "_evaluate_alt",
        "_evaluate_accuracy_v",
        "_evaluate_accuracy_h",
        "_evaluate_speed_accuracy",
        "_evaluate_vertical_speed",
        "_evaluate_speed",
    ]
    details_evaluators = [
        "_evaluate_ua_classification",
        "_evaluate_ua_classification_eu_category",
        "_evaluate_ua_classification_eu_class",
    ]

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
        injected_telemetry: injection.RIDAircraftState,
        injected_flight: injection.TestFlight,
        observed_flight: Flight,
        participant_id: ParticipantID,
        query_timestamp: datetime.datetime,
    ):
        """Implements fragment documented in `common_dictionary_evaluator_sp_flight.md`."""

        for generics_evaluator in self.flight_evaluators:
            getattr(self, generics_evaluator)(
                injected=injected_flight,
                sp_observed=observed_flight,
                dp_observed=None,
                participant=participant_id,
                query_timestamp=query_timestamp,
            )
        for generics_evaluator in self.telemetry_evaluators:
            getattr(self, generics_evaluator)(
                injected=injected_telemetry,
                sp_observed=observed_flight,
                dp_observed=None,
                participant=participant_id,
                query_timestamp=query_timestamp,
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

        for generics_evaluator in self.flight_evaluators:
            getattr(self, generics_evaluator)(
                injected=injected_flight,
                sp_observed=None,
                dp_observed=observed_flight,
                participant=participants[
                    0
                ],  # TODO: flatten 'participants', it always has a single value
                query_timestamp=query_timestamp,
            )
        for generics_evaluator in self.telemetry_evaluators:
            getattr(self, generics_evaluator)(
                injected=injected_telemetry,
                sp_observed=None,
                dp_observed=observed_flight,
                participant=participants[
                    0
                ],  # TODO: flatten 'participants', it always has a single value
                query_timestamp=query_timestamp,
            )

        # If the state is present, we do validate its content,
        # but its presence is optional
        if injected_telemetry.has_field_with_value("current_state"):
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

    def evaluate_sp_details(
        self,
        injected_details: injection.RIDFlightDetails,
        observed_details: FlightDetails,
        participant_id: ParticipantID,
        query_timestamp: datetime.datetime,
    ):
        """Implements fragment documented in `common_dictionary_evaluator_sp_flight_details.md`."""

        for generics_evaluator in self.details_evaluators:
            getattr(self, generics_evaluator)(
                injected=injected_details,
                sp_observed=observed_details,
                dp_observed=None,
                participant=participant_id,
                query_timestamp=query_timestamp,
            )

        self._evaluate_uas_id(observed_details.raw.get("uas_id"), [participant_id])
        self._evaluate_operator_id(None, observed_details.operator_id, [participant_id])
        self._evaluate_operator_location(
            None,
            None,
            None,
            observed_details.operator_location,
            observed_details.operator_altitude,
            observed_details.operator_altitude_type,
            [participant_id],
        )

    def evaluate_dp_details(
        self,
        injected_details: injection.RIDFlightDetails,
        observed_details: Optional[observation_api.GetDetailsResponse],
        participant_id: ParticipantID,
        query_timestamp: datetime.datetime,
    ):
        """Implements fragment documented in `common_dictionary_evaluator_dp_flight_details.md`."""

        for generics_evaluator in self.details_evaluators:
            getattr(self, generics_evaluator)(
                injected=injected_details,
                sp_observed=None,
                dp_observed=observed_details,
                participant=participant_id,
                query_timestamp=query_timestamp,
            )

        if not observed_details:
            return

        self._evaluate_arbitrary_uas_id(
            injected_details.get(
                "uas_id", injected_details.get("serial_number", None)
            ),  # fall back on seria number if no UAS ID
            observed_details.get("uas", {}).get("id", None),
            [participant_id],
        )

        operator_obs = observed_details.get("operator", {})

        self._evaluate_operator_id(
            injected_details.operator_id, operator_obs.get("id", None), [participant_id]
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
            [participant_id],
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
                            f"Invalid uas_id serial number: {serial_number}"
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
                "Timestamp field is present", participants
            ) as check:
                if timestamp_obs is None:
                    check.record_failed(
                        f"Timestamp not present",
                        details=f"The timestamp must be specified.",
                    )

            if timestamp_obs:
                with self._test_scenario.check(
                    "Timestamp consistency with Common Dictionary", participants
                ) as check:

                    try:
                        t_obs = StringBasedDateTime(timestamp_obs)
                        if t_obs.datetime.utcoffset().seconds != 0:
                            check.record_failed(
                                f"Timestamp must be relative to UTC: {t_obs}",
                            )
                    except ParserError as e:
                        check.record_failed(
                            f"Unable to parse timestamp: {timestamp_obs}",
                            details=f"Reason:  {e}",
                        )
                with self._test_scenario.check(
                    "Observed timestamp is consistent with injected one", participants
                ) as check:
                    t_inj = StringBasedDateTime(timestamp_inj)
                    if abs(t_inj.datetime - t_obs.datetime).total_seconds() > 1.0:
                        check.record_failed(
                            "Observed timestamp inconsistent with injected one",
                            details=f"Injected timestamp: {timestamp_inj} - Observed one: {timestamp_obs}",
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

    def _evaluate_speed(self, **generic_kwargs):
        """
        Evaluates Speed. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md`.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        def value_validator(val: float) -> float:
            if math.isclose(val, constants.SpecialSpeed):
                return val

            if val < 0:
                raise ValueError(f"Speed is less than 0")
            if val > constants.MaxSpeed:
                raise ValueError(f"Speed is greater than {constants.MaxSpeed}")
            return val

        def value_comparator(v1: Optional[float], v2: Optional[float]) -> bool:

            if v1 is None or v2 is None:
                return False

            return abs(v1 - v2) < constants.MinSpeedResolution

        self._generic_evaluator(
            "speed",
            "raw.current_state.speed",
            "current_state.speed",
            "Speed",
            value_validator,
            None,
            True,
            None,
            value_comparator,
            **generic_kwargs,
        )

    def _evaluate_track(
        self, track_inj: float, track_obs: Optional[float], participants: List[str]
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            with self._test_scenario.check(
                "Track Direction field is present", participants
            ) as check:
                if track_obs is None:
                    check.record_failed(
                        f"Track direction not present",
                        details=f"The track direction must be specified.",
                    )

            if track_obs is not None:
                with self._test_scenario.check(
                    "Track Direction consistency with Common Dictionary", participants
                ) as check:
                    if not (
                        constants.MinTrackDirection
                        <= track_obs
                        <= constants.MaxTrackDirection
                        or round(track_obs) == constants.SpecialTrackDirection
                    ):
                        check.record_failed(
                            f"Invalid track direction: {track_obs}",
                            details=f"The track direction shall be greater than -360 and less than {constants.MaxSpeed}. The Special Value {constants.SpecialSpeed} is allowed.",
                        )
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
                    )
                lng = position_obs.lng
                try:
                    lng = validate_lng(lng)
                except ValueError:
                    check.record_failed(
                        "Current Position contains an invalid longitude",
                        details=f"Invalid longitude: {lng}",
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
                        )

                with self._test_scenario.check(
                    "Height Type is consistent with injected one", participants
                ) as check:
                    if height_obs.reference != height_inj.reference:
                        check.record_failed(
                            "Observed Height type is inconsistent with injected one",
                            details=f"Observed height: {height_obs} - injected: {height_inj}",
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
                                details=f"Injected operational status: {value_inj} - Observed {value_obs}",
                            )

        else:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping Operational Status evaluation",
            )

    def _evaluate_ua_type(
        self,
        query_timestamp: datetime.datetime,
        **generic_kwargs,
    ):
        """
        Evaluates UA type. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md`.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        def value_validator(val: injection.UAType) -> injection.UAType:
            return injection.UAType(val)

        def observed_value_validator(check, observed_val: injection.UAType):

            if (
                self._rid_version == RIDVersion.f3411_19
                and observed_val == injection.UAType.HybridLift
            ) or (
                self._rid_version == RIDVersion.f3411_22a
                and observed_val == injection.UAType.VTOL
            ):
                check.record_failed(
                    "UA Type is inconsistent with RID version",
                    details=f"USS returned the UA Type {observed_val} which is not supported by the RID version used ({self._rid_version}).",
                    query_timestamps=[query_timestamp],
                )

        def value_comparator(
            v1: Optional[injection.UAType], v2: Optional[injection.UAType]
        ) -> bool:
            equivalent = {injection.UAType.HybridLift, injection.UAType.VTOL}

            if v1 in equivalent:
                return v2 in equivalent

            return v1 == v2

        self._generic_evaluator(
            "aircraft_type",
            "aircraft_type",
            "aircraft_type",
            "UA type",
            value_validator,
            observed_value_validator,
            False,
            injection.UAType.NotDeclared,
            value_comparator,
            query_timestamp=query_timestamp,
            **generic_kwargs,
        )

    def _evaluate_timestamp_accuracy(self, **generic_kwargs):
        """
        Evaluates Timestamp accuracy. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md`.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        TIMESTAMP_ACCURACY_PRECISION = 0.05

        def value_validator(val: float) -> float:
            if val < 0:
                raise ValueError("Timestamp accurary is less than 0")
            return val

        def value_comparator(v1: Optional[float], v2: Optional[float]) -> bool:

            if v1 is None or v2 is None:
                return False

            return abs(v1 - v2) < TIMESTAMP_ACCURACY_PRECISION

        self._generic_evaluator(
            "timestamp_accuracy",
            "raw.current_state.timestamp_accuracy",
            "current_state.timestamp_accuracy",
            "Timestamp accuracy",
            value_validator,
            None,
            True,
            None,
            value_comparator,
            **generic_kwargs,
        )

    def _evaluate_alt(self, **generic_kwargs):
        """
        Evaluates Geodetic Altitude. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md`.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        def value_comparator(v1: Optional[float], v2: Optional[float]) -> bool:

            if v1 is None or v2 is None:
                return False

            return abs(v1 - v2) < DISTANCE_TOLERANCE_M

        self._generic_evaluator(
            "position.alt",
            "raw.current_state.position.alt",
            "most_recent_position.alt",
            "Geodetic Altitude",
            None,
            None,
            True,
            None,
            value_comparator,
            **generic_kwargs,
        )

    def _evaluate_accuracy_v(self, **generic_kwargs):
        """
        Evaluates Geodetic Vertical Accuracy. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md`.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        def value_validator(val: VerticalAccuracy) -> VerticalAccuracy:
            return VerticalAccuracy(val)

        def value_comparator(
            v1: Optional[VerticalAccuracy], v2: Optional[VerticalAccuracy]
        ) -> bool:

            if v1 is None or v2 is None:
                return False

            return v1 == v2

        self._generic_evaluator(
            "position.accuracy_v",
            "raw.current_state.position.accuracy_v",
            "most_recent_position.accuracy_v",
            "Geodetic Vertical Accuracy",
            value_validator,
            None,
            True,
            None,
            value_comparator,
            **generic_kwargs,
        )

    def _evaluate_accuracy_h(self, **generic_kwargs):
        """
        Evaluates Horizontal Accuracy. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md`.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        def value_validator(val: HorizontalAccuracy) -> HorizontalAccuracy:
            return HorizontalAccuracy(val)

        def value_comparator(
            v1: Optional[HorizontalAccuracy], v2: Optional[HorizontalAccuracy]
        ) -> bool:

            if v1 is None or v2 is None:
                return False

            return v1 == v2

        self._generic_evaluator(
            "position.accuracy_h",
            "raw.current_state.position.accuracy_h",
            "most_recent_position.accuracy_h",
            "Horizontal Accuracy",
            value_validator,
            None,
            True,
            None,
            value_comparator,
            **generic_kwargs,
        )

    def _evaluate_speed_accuracy(self, **generic_kwargs):
        """
        Evaluates Speed Accuracy. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md`.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        def value_validator(val: SpeedAccuracy) -> SpeedAccuracy:
            return SpeedAccuracy(val)

        def value_comparator(
            v1: Optional[SpeedAccuracy], v2: Optional[SpeedAccuracy]
        ) -> bool:

            if v1 is None or v2 is None:
                return False

            return v1 == v2

        self._generic_evaluator(
            "speed_accuracy",
            "raw.current_state.speed_accuracy",
            "current_state.speed_accuracy",
            "Speed Accuracy",
            value_validator,
            None,
            True,
            None,
            value_comparator,
            **generic_kwargs,
        )

    def _evaluate_vertical_speed(self, **generic_kwargs):
        """
        Evaluates Vertical Speed. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md`.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        VERTICAL_SPEED_PRECISION = 0.1

        def value_validator(val: float) -> float:
            if val < -63:
                raise ValueError("Vertical speed is less than -63")
            if -63 > val > -62:
                raise ValueError("Vertical speed is between -63 and -62, exclusive")
            if val > 63:
                raise ValueError("Vertical speed is greather than 63")
            if 62 < val < 63:
                raise ValueError("Vertical speed is between 62 and 63, exclusive")
            return val

        def value_comparator(v1: Optional[float], v2: Optional[float]) -> bool:

            if v1 is None or v2 is None:
                return False

            return abs(v1 - v2) < VERTICAL_SPEED_PRECISION

        self._generic_evaluator(
            "vertical_speed",
            "raw.current_state.vertical_speed",
            "current_state.vertical_speed",
            "Vertical Speed",
            value_validator,
            None,
            True,
            None,
            value_comparator,
            **generic_kwargs,
        )

    def _evaluate_ua_classification(
        self,
        injected: injection.RIDFlightDetails,
        sp_observed: Optional[FlightDetails],
        dp_observed: Optional[observation_api.GetDetailsResponse],
        participant: ParticipantID,
        query_timestamp: datetime.datetime,
    ):
        """
        Evaluates UA classification type. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md`.
        Note that the classification type is defined implicitly by presence of field 'eu_classification' or not:
            > When this field is specified, the Classification Type is "European Union".  If no other classification
            > field is specified, the Classification Type is "Undeclared".

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        if self._rid_version == RIDVersion.f3411_19:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping UA classification type evaluation",
            )
            return

        injected_ua_classification: Optional[str] = None
        if "eu_classification" in injected:
            injected_ua_classification = "eu_classification"

        observed_ua_classification: Optional[str] = None
        if sp_observed is not None:
            if sp_observed.raw.has_field_with_value("eu_classification"):
                observed_ua_classification = "eu_classification"
        elif dp_observed is not None:
            if dp_observed.has_field_with_value(
                "uas"
            ) and dp_observed.uas.has_field_with_value("eu_classification"):
                observed_ua_classification = "eu_classification"
        else:
            raise ValueError("No observed flight provided.")

        with self._test_scenario.check(
            "UA classification type is consistent with injected value",
            participant,
        ) as check:
            if dp_observed is not None and observed_ua_classification is None:
                pass  # C8

            elif injected_ua_classification != observed_ua_classification:  # C7 / C10
                check.record_failed(
                    "UA classification type is inconsistent with injected value.",
                    details=f"USS returned UA classification type {observed_ua_classification} yet the type injected was {injected_ua_classification}.",
                    query_timestamps=[query_timestamp],
                )

    def _evaluate_ua_classification_eu_category(
        self, injected: injection.RIDFlightDetails, **generic_kwargs
    ):
        """
        Evaluates UA classification 'category' field for 'European Union' type. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md`.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        if self._rid_version == RIDVersion.f3411_19:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping UA classification 'category' field for 'European Union' type",
            )
            return
        if not injected.has_field_with_value("eu_classification"):
            # skip if UA classification type is not 'European Union' type
            return

        def cat_value_validator(
            val: UAClassificationEUCategory,
        ) -> UAClassificationEUCategory:
            return UAClassificationEUCategory(val)

        def cat_value_comparator(
            v1: Optional[UAClassificationEUCategory],
            v2: Optional[UAClassificationEUCategory],
        ) -> bool:

            if v1 is None or v2 is None:
                return False

            return v1 == v2

        self._generic_evaluator(
            "eu_classification.category",
            "raw.eu_classification.category",
            "uas.eu_classification.category",
            "UA classification 'category' field for 'European Union' type",
            cat_value_validator,
            None,
            False,
            UAClassificationEUCategory.EUCategoryUndefined,
            cat_value_comparator,
            injected,
            **generic_kwargs,
        )

    def _evaluate_ua_classification_eu_class(
        self, injected: injection.RIDFlightDetails, **generic_kwargs
    ):
        """
        Evaluates UA classification 'class' field for 'European Union' type. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md`.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        if self._rid_version == RIDVersion.f3411_19:
            self._test_scenario.record_note(
                key="skip_reason",
                message=f"Unsupported version {self._rid_version}: skipping UA classification 'class' field for 'European Union' type",
            )
            return
        if not injected.has_field_with_value("eu_classification"):
            # skip if UA classification type is not 'European Union' type
            return

        def class_value_validator(
            val: UAClassificationEUClass,
        ) -> UAClassificationEUClass:
            return UAClassificationEUClass(val)

        def class_value_comparator(
            v1: Optional[UAClassificationEUClass], v2: Optional[UAClassificationEUClass]
        ) -> bool:

            if v1 is None or v2 is None:
                return False

            return v1 == v2

        self._generic_evaluator(
            "eu_classification.class",
            "raw.eu_classification.class",
            "uas.eu_classification.class",
            "UA classification 'class' field for 'European Union' type",
            class_value_validator,
            None,
            False,
            UAClassificationEUClass.EUClassUndefined,
            class_value_comparator,
            injected,
            **generic_kwargs,
        )

    def _generic_evaluator(
        self,
        injected_field_name: str,
        sp_field_name: str,
        dp_field_name: str,
        field_human_name: str,
        value_validator: Optional[Callable[[T], T]],
        observed_value_validator: Optional[Callable[[PendingCheck, T], None]],
        injection_required_field: bool,
        unknown_value: Optional[T],
        value_comparator: Callable[[Optional[T], Optional[T]], bool],
        injected: Union[
            injection.TestFlight,
            injection.RIDAircraftState,
            injection.RIDFlightDetails,
        ],
        sp_observed: Optional[Union[Flight, FlightDetails]],
        dp_observed: Optional[
            Union[observation_api.Flight, observation_api.GetDetailsResponse]
        ],
        participant: ParticipantID,
        query_timestamp: datetime.datetime,
    ):

        """
        Generic evaluator of a field. Exactly one of sp_observed or dp_observed must be provided.
        See as well `common_dictionary_evaluator.md` for an overview of the different cases 'Cn' referred to in this function.

        TODO: The generic evaluator cannot detect that a SP/DP field is missing if the default value is injected since the default dicts may
        just set the default value when the SP/DP returns nothing. See #949

        Args:
            injected_field_name: The name of the field on the injected flight object to test. If starts with telemetry, current telemetry is used
            sp_field_name: The name of the field on the sp observed flight object to test
            dp_field_name: The name of the field on the dp observed flight object to test
            field_human_name: The display name of the field to test
            value_validator: If not None, pass values through this function. You may raise ValueError to indicate errors.
            observed_value_validator: If not None, will be called with check and observed value, for additional verifications
            injection_required_field: Boolean to indicate we need to check the case where nothing has been injected (C6)
            unknown_value: The default value that needs to be returned when nothing has been injected
            value_comparator: Function that need to return True if both parameters are equal
            injected: injected data (flight, telemetry or details).
            sp_observed: flight (or details) observed through the SP API.
            dp_observed: flight (or details) observed through the observation API.
            participant: participant providing the API through which the value was observed.
            query_timestamp: timestamp of the observation query.

        Raises:
            ValueError: if a test operation wasn't performed correctly by uss_qualifier.
        """

        def dotted_get(obj: Any, key: str) -> Optional[T]:
            val: Any = obj
            for k in key.split("."):
                if val is None:
                    return val
                if isinstance(val, dict) and k in val:
                    val = val[k]
                else:
                    val = getattr(val, k)
            return val

        injected_val: Optional[T] = dotted_get(injected, injected_field_name)
        if injected_val is not None:

            if value_validator is not None:
                try:
                    injected_val = value_validator(injected_val)
                except ValueError as e:
                    raise ValueError(
                        f"Invalid {field_human_name} {injected_val} injected", e
                    )

        observed_val: Optional[T]
        if sp_observed is not None:
            observed_val = dotted_get(sp_observed, sp_field_name)
        elif dp_observed is not None:
            observed_val = dotted_get(dp_observed, dp_field_name)
        else:
            raise ValueError("No observed flight provided.")

        with self._test_scenario.check(
            f"{field_human_name} is exposed correctly",
            participant,
        ) as check:
            if sp_observed is not None:
                if observed_val is None:  # C3
                    check.record_failed(
                        f"{field_human_name} is missing",
                        details=f"SP did not return any {field_human_name}",
                        query_timestamps=[query_timestamp],
                        additional_data={"RIDCommonDictionaryEvaluatorCheckID": "C3"},
                    )

            if observed_val is not None:  # C5 / C9
                if value_validator is not None:
                    try:
                        value_validator(observed_val)
                    except ValueError:
                        check.record_failed(
                            f"{field_human_name} is invalid",
                            details=f"USS returned an invalid {field_human_name}: {observed_val}.",
                            query_timestamps=[query_timestamp],
                            additional_data={
                                "RIDCommonDictionaryEvaluatorCheckID": "C5"
                                if sp_observed
                                else "C9"
                            },
                        )

                if observed_value_validator is not None:
                    observed_value_validator(check, observed_val)

        with self._test_scenario.check(
            f"{field_human_name} is consistent with injected value",
            participant,
        ) as check:

            if dp_observed is not None and observed_val is None:
                pass  # C8

            elif injected_val is None:

                if injection_required_field:
                    raise ValueError(
                        f"Invalid {field_human_name} value injected. Injection is marked as required, but we injected a None value. This should have been caught by the injection api."
                    )

                if observed_val != unknown_value:  # C6 / C10
                    check.record_failed(
                        f"{field_human_name} is inconsistent, expected '{unknown_value}' since no value was injected",
                        details=f"USS returned the UA type {observed_val} yet no value was injected. Since '{field_human_name}' is a required field of SP API, the SP should map this to '{unknown_value}' and the DP should expose the same value.",
                        query_timestamps=[query_timestamp],
                        additional_data={
                            "RIDCommonDictionaryEvaluatorCheckID": "C6"
                            if sp_observed
                            else "C10"
                        },
                    )

            elif not value_comparator(injected_val, observed_val):  # C7 / C10
                check.record_failed(
                    f"{field_human_name} is inconsistent with injected value",
                    details=f"USS returned the {field_human_name} {observed_val}, yet the value {injected_val} was injected.",
                    query_timestamps=[query_timestamp],
                    additional_data={
                        "RIDCommonDictionaryEvaluatorCheckID": "C7"
                        if sp_observed
                        else "C10"
                    },
                )
