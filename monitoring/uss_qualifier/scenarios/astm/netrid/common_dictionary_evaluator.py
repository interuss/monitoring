from typing import List, Optional
from monitoring.monitorlib.fetch.rid import (
    FetchedUSSFlightDetails,
    FetchedUSSFlights,
    FetchedFlights,
    FlightDetails,
)
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.geo import validate_lat, validate_lng
from uas_standards.ansi_cta_2063_a import SerialNumber
from uas_standards.astm.f3411 import v22a


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
        self, observed_flights: FetchedFlights, participants: List[str]
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            for f in observed_flights.flights:
                self.evaluate_operational_status(
                    f.v22a_value.get("current_state", {}).get("operational_status"),
                    participants,
                )

    def evaluate_sp_details(self, details: FlightDetails, participants: List[str]):
        if self._rid_version == RIDVersion.f3411_22a:
            self.evaluate_uas_id(details.v22a_value.get("uas_id"), participants)
            self.evaluate_operator_id(
                details.v22a_value.get("operator_id"), participants
            )
            self.evaluate_operator_location(
                details.v22a_value.get("operator_location"), participants
            )

    def evaluate_uas_id(self, value: Optional[v22a.api.UASID], participants: List[str]):
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
                        "UAS ID not present as required by the Common Dictionary definition",
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

    def evaluate_operator_id(self, value: Optional[str], participants: List[str]):
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

    def evaluate_operator_location(
        self, value: Optional[v22a.api.OperatorLocation], participants: List[str]
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            if value:
                with self._test_scenario.check(
                    "Operator Location consistency with Common Dictionary", participants
                ) as check:
                    lat = value.position.lat
                    try:
                        lat = validate_lat(lat)
                    except ValueError:
                        check.record_failed(
                            "Operator Location contains an invalid latitude",
                            details=f"Invalid latitude: {lat}",
                            severity=Severity.Medium,
                        )
                    lng = value.position.lng
                    try:
                        lng = validate_lng(lng)
                    except ValueError:
                        check.record_failed(
                            "Operator Location contains an invalid longitude",
                            details=f"Invalid longitude: {lng}",
                            severity=Severity.Medium,
                        )

                alt = value.get("altitude")
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

                    alt_type = value.get("altitude_type")
                    if alt_type:
                        with self._test_scenario.check(
                            "Operator Altitude Type consistency with Common Dictionary",
                            participants,
                        ) as check:
                            try:
                                v22a.api.OperatorLocationAltitude_type(
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

    def evaluate_operational_status(
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
