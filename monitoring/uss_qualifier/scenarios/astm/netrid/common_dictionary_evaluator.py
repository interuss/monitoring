from typing import List, Optional
from monitoring.monitorlib.fetch.rid import FetchedUSSFlightDetails
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from monitoring.monitorlib.rid import RIDVersion
from uas_standards.ansi_cta_2063_a import SerialNumber
from uas_standards.astm.f3411.v22a.api import UASID
from loguru import logger


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

    def evaluate_sp_details_response(
        self, sp_response: FetchedUSSFlightDetails, participants: List[str]
    ):
        if self._rid_version == RIDVersion.f3411_22a:
            self.evaluate_uas_id(sp_response.details.v22a_value.uas_id, participants)
            self.evaluate_operator_id(
                sp_response.details.v22a_value.operator_id, participants
            )

    def evaluate_uas_id(self, value: Optional[UASID], participants: List[str]):
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
                else sum([0 if value.get(v, None) is None else 1 for v in formats_keys])
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

            serial_number = value.get("serial_number", None)
            if serial_number:
                with self._test_scenario.check(
                    "UAS ID (Serial Number format) consistency with Common Dictionary",
                    participants,
                ) as check:
                    if not SerialNumber(serial_number).valid:
                        check.record_failed(
                            f"Invalid uas_id serial number: {serial_number}",
                            participants,
                        )
                    else:
                        check.record_passed()

            # TODO: Add registration id format check
            # TODO: Add utm id format check
            # TODO: Add specific session id format check
        else:
            self._test_scenario.record_note(
                f"Unsupported version {self._rid_version}: skipping UAS ID evaluation"
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
                f"Unsupported version {self._rid_version}: skipping Operator ID evaluation"
            )
