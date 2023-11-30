from datetime import datetime
from typing import Dict, Optional, List

from monitoring.monitorlib import schema_validation
from monitoring.monitorlib.fetch.rid import ISA, FetchedISA, FetchedISAs
from monitoring.monitorlib.mutate.rid import ChangedISA
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.scenarios.scenario import (
    PendingCheck,
    GenericTestScenario,
)

MAX_SKEW = 1e-6  # seconds maximum difference between expected and actual timestamps


class ISAValidator(object):
    """Wraps the validation logic for an ISA that was returned by the DSS.
    It will compare the returned ISA with the parameters specified at its creation.
    """

    _main_check: PendingCheck
    _scenario: GenericTestScenario
    # Params are optional: if they are not set, the field contents will not be checked
    _isa_params: Optional[Dict[str, any]]
    _dss_id: List[str]
    _rid_version: RIDVersion

    def __init__(
        self,
        main_check: PendingCheck,
        scenario: GenericTestScenario,
        isa_params: Optional[Dict[str, any]],
        dss_id: List[str],
        rid_version: RIDVersion,
    ):
        self._main_check = main_check
        self._scenario = scenario
        self._isa_params = isa_params
        self._dss_id = dss_id
        self._rid_version = rid_version

    def _fail_sub_check(
        self, _sub_check: PendingCheck, _summary: str, _details: str, t_dss: datetime
    ) -> None:
        """Fails with Medium severity the sub_check and with High severity the main check."""

        _sub_check.record_failed(
            summary=_summary,
            severity=Severity.Medium,
            details=_details,
            query_timestamps=[t_dss],
        )

        self._main_check.record_failed(
            summary=f"ISA request succeeded, but the DSS response is not valid: {_summary}",
            severity=Severity.High,
            details=_details,
            query_timestamps=[t_dss],
        )

    def _validate_isa(
        self,
        expected_isa_id: str,
        dss_isa: ISA,
        t_dss: datetime,
        previous_version: Optional[
            str
        ] = None,  # If set, we control that the version changed
        expected_version: Optional[
            str
        ] = None,  # If set, we control that the version has not changed
    ) -> None:
        isa_id = expected_isa_id
        dss_id = self._dss_id
        with self._scenario.check("ISA ID matches", dss_id) as sub_check:
            if isa_id != dss_isa.id:
                self._fail_sub_check(
                    sub_check,
                    "DSS did not return correct ISA",
                    f"Expected ISA ID {dss_id} but got {dss_isa.id}",
                    t_dss,
                )

        if previous_version is not None:
            with self._scenario.check("ISA version changed", dss_id) as sub_check:
                if dss_isa.version == previous_version:
                    self._fail_sub_check(
                        sub_check,
                        "ISA version was not updated",
                        f"Got old version {previous_version} while expecting new version",
                        t_dss,
                    )

        if expected_version is not None:
            with self._scenario.check("ISA version matches", dss_id) as sub_check:
                if dss_isa.version != expected_version:
                    self._fail_sub_check(
                        sub_check,
                        "ISA version is not the previously held one, although no modification was done to the ISA",
                        f"Got old version {dss_isa.version} while expecting {expected_version}",
                        t_dss,
                    )

        with self._scenario.check("ISA version format", dss_id) as sub_check:
            if not all(c not in "\0\t\r\n#%/:?@[\]" for c in dss_isa.version):
                self._fail_sub_check(
                    sub_check,
                    f"DSS returned ISA (ID {isa_id}) with invalid version format",
                    f"DSS returned an ISA with a version that is not URL-safe: {dss_isa.version}",
                    t_dss,
                )

        # Optionally check the ISA's fields if the creation parameters were specified
        if self._isa_params is not None:
            with self._scenario.check("ISA start time matches", dss_id) as sub_check:
                expected_start = self._isa_params["start_time"]
                if (
                    abs((dss_isa.time_start - expected_start).total_seconds())
                    > MAX_SKEW
                ):
                    self._fail_sub_check(
                        sub_check,
                        f"DSS returned ISA (ID {isa_id}) with incorrect start time",
                        f"DSS should have returned an ISA with a start time of {expected_start}, but instead the ISA returned had a start time of {dss_isa.time_start}",
                        t_dss,
                    )

            with self._scenario.check("ISA end time matches", dss_id) as sub_check:
                expected_end = self._isa_params["end_time"]
                if abs((dss_isa.time_end - expected_end).total_seconds()) > MAX_SKEW:
                    self._fail_sub_check(
                        sub_check,
                        f"DSS returned ISA (ID {isa_id}) with incorrect end time",
                        f"DSS should have returned an ISA with an end time of {expected_end}, but instead the ISA returned had an end time of {dss_isa.time_end}",
                        t_dss,
                    )

            with self._scenario.check("ISA URL matches", dss_id) as sub_check:
                expected_flights_url = self._rid_version.flights_url_of(
                    self._isa_params["uss_base_url"]
                )
                actual_flights_url = dss_isa.flights_url
                if actual_flights_url != expected_flights_url:
                    self._fail_sub_check(
                        sub_check,
                        f"DSS returned ISA (ID {isa_id}) with incorrect URL",
                        f"DSS should have returned an ISA with a flights URL of {expected_flights_url}, but instead the ISA returned had a flights URL of {actual_flights_url}",
                        t_dss,
                    )

        # TODO consider adding notification validation

    def validate_fetched_isa(
        self,
        expected_isa_id: str,
        fetched_isa: FetchedISA,
        expected_version: str,
    ):
        """Validates the DSS reply to an ISA fetch request."""
        t_dss = fetched_isa.query.request.timestamp

        with self._scenario.check("ISA response format", self._dss_id) as sub_check:
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_get_isa_response_path,
                fetched_isa.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                self._fail_sub_check(
                    sub_check,
                    "GET ISA response format was invalid",
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    t_dss,
                )

        self._validate_isa(
            expected_isa_id, fetched_isa.isa, t_dss, expected_version=expected_version
        )

    def validate_mutated_isa(
        self,
        expected_isa_id: str,
        mutated_isa: ChangedISA,
        previous_version: Optional[str] = None,
    ):
        """
        Validates the DSS reply to an ISA mutation request.
        Note that both creating or updating an ISA count as a mutation: the only difference from the
        perspective of this function is that previous_version is set in the case of a mutation and None
        in the case of a creation.
        """
        t_dss = mutated_isa.query.request.timestamp

        with self._scenario.check("ISA response format", self._dss_id) as sub_check:
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_put_isa_response_path,
                mutated_isa.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                sub_check.record_failed(
                    "PUT ISA response format was invalid",
                    Severity.Medium,
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    query_timestamps=[t_dss],
                )

        self._validate_isa(
            expected_isa_id,
            mutated_isa.isa,
            t_dss,
            previous_version=previous_version,
            expected_version=None,
        )

    def validate_deleted_isa(
        self,
        expected_isa_id: str,
        deleted_isa: ChangedISA,
        expected_version: str,
    ):
        """Validates the DSS reply to an ISA deletion request."""
        t_dss = deleted_isa.query.request.timestamp

        with self._scenario.check("ISA response format", self._dss_id) as sub_check:
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_delete_isa_response_path,
                deleted_isa.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                sub_check.record_failed(
                    "PUT ISA response format was invalid",
                    Severity.Medium,
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    query_timestamps=[t_dss],
                )

        self._validate_isa(
            expected_isa_id, deleted_isa.isa, t_dss, expected_version=expected_version
        )

    def validate_searched_isas(
        self,
        fetched_isas: FetchedISAs,
        expected_versions: Dict[str, str],
    ):
        """Validates the DSS reply to an ISA search request:
        based on the ISA ID's present in expected_versions, it will verify the content of the returned ISA's.
        Note that ISAs that are not part of the test are entirely ignored.
        """
        for isa_id, isa_version in expected_versions.items():
            self._validate_isa(
                isa_id,
                fetched_isas.isas[isa_id],
                fetched_isas.query.request.timestamp,
                expected_version=expected_versions[isa_id],
            )
