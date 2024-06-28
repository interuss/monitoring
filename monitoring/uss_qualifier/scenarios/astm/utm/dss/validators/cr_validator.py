from datetime import datetime
from typing import Optional, List

from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21.api import (
    EntityID,
    ConstraintReference,
    ChangeConstraintReferenceResponse,
    EntityOVN,
    GetConstraintReferenceResponse,
    QueryConstraintReferencesResponse,
    PutConstraintReferenceParameters,
    ConstraintReference,
    ChangeConstraintReferenceResponse,
)

from monitoring.monitorlib import schema_validation, fetch
from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.monitorlib.schema_validation import F3548_21
from monitoring.uss_qualifier.scenarios.astm.utm.dss.validators import (
    fail_with_schema_errors,
)
from monitoring.uss_qualifier.scenarios.scenario import PendingCheck, TestScenario

TIME_TOLERANCE_SEC = 1
"""tolerance when comparing created vs returned timestamps"""


class ConstraintReferenceValidator:
    """
    Wraps the validation logic for an constraint reference that was returned by a DSS

    It will compare the provided CR with the parameters specified at its creation.
    """

    _main_check: PendingCheck
    """
    The overarching check corresponding to the general validation of a CR.
    This check will be failed if any of the sub-checks carried out by this validator fail.
    """

    _scenario: TestScenario
    """
    Scenario in which this validator is being used. Will be used to register checks.
    """

    _cr_params: Optional[PutConstraintReferenceParameters]
    _pid: List[str]
    """Participant ID(s) to use for the checks"""

    def __init__(
        self,
        main_check: PendingCheck,
        scenario: TestScenario,
        expected_manager: str,
        participant_id: List[str],
        cr_params: Optional[PutConstraintReferenceParameters],
    ):
        self._main_check = main_check
        self._scenario = scenario
        self._pid = participant_id
        self._cr_params = cr_params
        self._expected_manager = expected_manager
        vol_collection = Volume4DCollection.from_f3548v21(cr_params.extents)
        self._expected_start = vol_collection.time_start.datetime
        self._expected_end = vol_collection.time_end.datetime

    def _fail_sub_check(
        self, sub_check: PendingCheck, summary: str, details: str, t_dss: datetime
    ) -> None:
        """
        Fail the passed sub check with the passed summary and details, and fail
        the main check with the passed details.

        Note that this method should only be used to fail sub-checks related to the CONTENT of the CR,
        but not its FORMAT, as the main-check should only be pertaining to the content.

        The provided timestamp is forwarded into the query_timestamps of the check failure.
        """
        sub_check.record_failed(
            summary=summary,
            details=details,
            query_timestamps=[t_dss],
        )

        self._main_check.record_failed(
            summary=f"Invalid CR returned by the DSS: {summary}",
            details=details,
            query_timestamps=[t_dss],
        )

    def _validate_cr(
        self,
        expected_entity_id: EntityID,
        dss_cr: ConstraintReference,
        t_dss: datetime,
        previous_version: Optional[int],
        expected_version: Optional[int],
        previous_ovn: Optional[str],
        expected_ovn: Optional[str],
    ) -> None:
        """
        Args:
            expected_entity_id: the ID we expect to find in the entity
            dss_cr: the CR returned by the DSS
            t_dss: timestamp of the query to the DSS for failure reporting
            previous_ovn: previous OVN of the entity, if we are verifying a mutation
            expected_ovn: expected OVN of the entity, if we are verifying a read query
            previous_version: previous version of the entity, if we are verifying a mutation
            expected_version: expected version of the entity, if we are verifying a read query
        """

        with self._scenario.check(
            "Returned constraint reference ID is correct", self._pid
        ) as check:
            if dss_cr.id != expected_entity_id:
                self._fail_sub_check(
                    check,
                    summary=f"Returned CR ID is incorrect",
                    details=f"Expected CR ID {expected_entity_id}, got {dss_cr.id}",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Returned constraint reference has a manager", self._pid
        ) as check:
            # Check for empty string. None should have failed the schema check earlier
            if not dss_cr.manager:
                self._fail_sub_check(
                    check,
                    summary="No CR manager was specified",
                    details=f"Expected: {self._expected_manager}, got an empty or undefined string",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Returned constraint reference manager is correct", self._pid
        ) as check:
            if dss_cr.manager != self._expected_manager:
                self._fail_sub_check(
                    check,
                    summary="Returned manager is incorrect",
                    details=f"Expected {self._expected_manager}, got {dss_cr.manager}",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Returned constraint reference has an USS base URL", self._pid
        ) as check:
            # If uss_base_url is not present, or it is None or Empty, we should fail:
            if "uss_base_url" not in dss_cr or not dss_cr.uss_base_url:
                self._fail_sub_check(
                    check,
                    summary="Returned CR has no USS base URL",
                    details="The CR returned by the DSS has no USS base URL when it should have one",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Returned constraint reference base URL is correct", self._pid
        ) as check:
            if dss_cr.uss_base_url != self._cr_params.uss_base_url:
                self._fail_sub_check(
                    check,
                    summary="Returned USS Base URL does not match provided one",
                    details=f"Provided: {self._cr_params.uss_base_url}, Returned: {dss_cr.uss_base_url}",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Returned constraint reference has a start time", self._pid
        ) as check:
            if "time_start" not in dss_cr or dss_cr.time_start is None:
                self._fail_sub_check(
                    check,
                    summary="Returned CR has no start time",
                    details="The constraint reference returned by the DSS has no start time when it should have one",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Returned constraint reference has an end time", self._pid
        ) as check:
            if "time_end" not in dss_cr or dss_cr.time_end is None:
                self._fail_sub_check(
                    check,
                    summary="Returned CR has no end time",
                    details="The constraint reference returned by the DSS has no end time when it should have one",
                    t_dss=t_dss,
                )

        with self._scenario.check("Returned start time is correct", self._pid) as check:
            if (
                abs(
                    dss_cr.time_start.value.datetime - self._expected_start
                ).total_seconds()
                > TIME_TOLERANCE_SEC
            ):
                self._fail_sub_check(
                    check,
                    summary="Returned start time does not match provided one",
                    details=f"Provided: {self._cr_params.start_time}, Returned: {dss_cr.time_start}",
                    t_dss=t_dss,
                )

        with self._scenario.check("Returned end time is correct", self._pid) as check:
            if (
                abs(dss_cr.time_end.value.datetime - self._expected_end).total_seconds()
                > TIME_TOLERANCE_SEC
            ):
                self._fail_sub_check(
                    check,
                    summary="Returned end time does not match provided one",
                    details=f"Provided: {self._cr_params.end_time}, Returned: {dss_cr.time_end}",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Returned constraint reference has an OVN", self._pid
        ) as check:
            if dss_cr.ovn is None:
                self._fail_sub_check(
                    check,
                    summary="Returned CR has no OVN",
                    details="The constraint reference returned by the DSS has no OVN when it should have one",
                    t_dss=t_dss,
                )

        if previous_ovn is not None:
            with self._scenario.check(
                "Mutated constraint reference OVN is updated", self._pid
            ) as check:
                if dss_cr.ovn == previous_ovn:
                    self._fail_sub_check(
                        check,
                        summary="Returned CR OVN was not updated",
                        details=f"Expected OVN to be different from {previous_ovn}, but it was not",
                        t_dss=t_dss,
                    )

        if expected_ovn is not None:
            with self._scenario.check(
                "Non-mutated constraint reference keeps the same OVN", self._pid
            ) as check:
                if dss_cr.ovn != expected_ovn:
                    self._fail_sub_check(
                        check,
                        summary="Returned CR OVN was updated",
                        details=f"Expected OVN to be {expected_ovn}, Returned: {dss_cr.ovn}",
                        t_dss=t_dss,
                    )

        # If the previous version is not None, we are dealing with a mutation:
        if previous_version is not None:
            with self._scenario.check(
                "Mutated constraint reference version is updated", self._pid
            ) as check:
                # TODO confirm that a mutation should imply a version update
                if dss_cr.version == previous_version:
                    self._fail_sub_check(
                        check,
                        summary="Returned CR version was not updated",
                        details=f"Expected version to be different from {previous_version}, but it was not",
                        t_dss=t_dss,
                    )

        # TODO version _might_ get incremented due to changes caused outside of the uss_qualifier
        #  and we should probably check if it is equal or higher. Leaving as-is for now.
        if expected_version is not None:
            with self._scenario.check(
                "Non-mutated constraint reference keeps the same version",
                self._pid,
            ) as check:
                if dss_cr.version != expected_version:
                    self._fail_sub_check(
                        check,
                        summary="Returned CR version was updated",
                        details=f"Expected version to be {expected_version}, Returned: {dss_cr.version}",
                        t_dss=t_dss,
                    )

        # TODO add check for:
        #  - subscription ID of the CR (based on passed parameters, if these were set)

    def _validate_put_cr_response_schema(
        self, cr_query: fetch.Query, t_dss: datetime, action: str
    ) -> bool:
        """Validate response bodies for creation and mutation of CRs.
        Returns 'False' if the schema validation failed, 'True' otherwise.
        """

        check_name = (
            "Create constraint reference response format conforms to spec"
            if action == "create"
            else "Mutate constraint reference response format conforms to spec"
        )

        with self._scenario.check(check_name, self._pid) as check:
            errors = schema_validation.validate(
                F3548_21.OpenAPIPath,
                F3548_21.ChangeConstraintReferenceResponse,
                cr_query.response.json,
            )
            if errors:
                fail_with_schema_errors(check, errors, t_dss)
                return False

        return True

    def validate_created_cr(
        self, expected_cr_id: EntityID, new_cr: fetch.Query
    ) -> None:
        """Validate a CR that was just explicitly created, meaning
        we don't have a previous version to compare to, and we expect it to not be an implicit one."""

        t_dss = new_cr.request.timestamp

        # Validate the response schema
        if not self._validate_put_cr_response_schema(new_cr, t_dss, "create"):
            return

        # Expected to pass given that we validated the JSON against the schema
        parsed_resp = new_cr.parse_json_result(ChangeConstraintReferenceResponse)

        # Validate the CR itself
        self._validate_cr(
            expected_entity_id=expected_cr_id,
            dss_cr=parsed_resp.constraint_reference,
            t_dss=t_dss,
            previous_version=None,
            expected_version=None,
            previous_ovn=None,
            expected_ovn=None,
        )

    def validate_fetched_cr(
        self,
        expected_cr_id: EntityID,
        fetched_cr: fetch.Query,
        expected_version: int,
        expected_ovn: EntityOVN,
    ) -> None:
        """Validate a CR that was directly queried by its ID."""

        t_dss = fetched_cr.request.timestamp

        # Validate the response schema
        with self._scenario.check(
            "Get constraint reference response format conforms to spec",
            self._pid,
        ) as check:
            errors = schema_validation.validate(
                F3548_21.OpenAPIPath,
                F3548_21.GetConstraintReferenceResponse,
                fetched_cr.response.json,
            )
            if errors:
                fail_with_schema_errors(check, errors, t_dss)

        parsed_resp = fetched_cr.parse_json_result(GetConstraintReferenceResponse)
        # Validate the CR itself
        self._validate_cr(
            expected_entity_id=expected_cr_id,
            dss_cr=parsed_resp.constraint_reference,
            t_dss=t_dss,
            previous_version=None,
            expected_version=expected_version,
            previous_ovn=None,
            expected_ovn=expected_ovn,
        )

    def validate_searched_cr(
        self,
        expected_cr_id: EntityID,
        search_response: fetch.Query,
        expected_ovn: str,
        expected_version: int,
    ) -> None:
        """Validate a CR that was retrieved through search.
        Note that the callers need to pass the entire response from the DSS, as the schema check
        will be performed on the entire response, not just the CR itself.
        However, only the expected CR is checked for the correctness of its contents."""

        t_dss = search_response.request.timestamp

        # Validate the response schema
        self.validate_searched_cr_format(search_response, t_dss)

        resp_parsed = search_response.parse_json_result(
            QueryConstraintReferencesResponse
        )

        by_id = {cr.id: cr for cr in resp_parsed.constraint_references}

        with self._scenario.check(
            "Expected constraint reference is in search results", self._pid
        ) as check:
            if expected_cr_id not in by_id:
                self._fail_sub_check(
                    check,
                    summary="Created CR is not present in search results",
                    details=f"The CR with ID {expected_cr_id} was expected to be found in the search results, but these only contained the following entities: {by_id.keys()}",
                    t_dss=t_dss,
                )
                # Depending on the severity defined in the documentation, the above might not raise an exception,
                # and we should still stop here if the check failed.
                return

        cr = by_id[expected_cr_id]

        # Validate the CR itself
        self._validate_cr(
            expected_entity_id=expected_cr_id,
            dss_cr=cr,
            t_dss=t_dss,
            previous_ovn=None,
            expected_ovn=expected_ovn,
            previous_version=None,
            expected_version=expected_version,
        )

    def validate_searched_cr_format(
        self, search_response: fetch.Query, t_dss: datetime
    ) -> None:
        # Validate the response schema
        with self._scenario.check(
            "Search constraint reference response format conforms to spec",
            self._pid,
        ) as check:
            errors = schema_validation.validate(
                F3548_21.OpenAPIPath,
                F3548_21.QueryConstraintReferenceResponse,
                search_response.response.json,
            )
            if errors:
                fail_with_schema_errors(check, errors, t_dss)

    def validate_deleted_cr(
        self,
        expected_cr_id: EntityID,
        deleted_cr: fetch.Query,
        expected_ovn: str,
        expected_version: int,
    ) -> None:

        t_dss = deleted_cr.request.timestamp

        # Validate the response schema
        with self._scenario.check(
            "Delete constraint reference response format conforms to spec",
            self._pid,
        ) as check:
            errors = schema_validation.validate(
                F3548_21.OpenAPIPath,
                F3548_21.ChangeConstraintReferenceResponse,
                deleted_cr.response.json,
            )
            if errors:
                fail_with_schema_errors(check, errors, t_dss)

        cr_resp = deleted_cr.parse_json_result(ChangeConstraintReferenceResponse)

        # Validate the CR itself
        self._validate_cr(
            expected_entity_id=expected_cr_id,
            dss_cr=cr_resp.constraint_reference,
            t_dss=t_dss,
            previous_ovn=None,
            expected_ovn=expected_ovn,
            previous_version=None,
            expected_version=expected_version,
        )
