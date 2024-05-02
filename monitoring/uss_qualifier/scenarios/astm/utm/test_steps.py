from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union, Set
from implicitdict import ImplicitDict
from monitoring.monitorlib import schema_validation, fetch
from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    Volume4D,
    OperationalIntentReference,
    GetOperationalIntentDetailsResponse,
    EntityID,
    ExchangeRecord,
)
from uas_standards.astm.f3548.v21.constants import Scope
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    UasState,
    AirspaceUsageState,
)
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlanner,
)
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.uss_qualifier.scenarios.astm.utm.evaluation import (
    validate_op_intent_details,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenarioType,
    TestRunCannotContinueError,
)
from uas_standards.interuss.automated_testing.scd.v1.api import InjectFlightRequest


class OpIntentValidator(object):
    """
    This class enables the validation of the sharing (or not) of an operational
    intent with the DSS. It does so by comparing the operational intents found
    in the area of the intent before and after a planning attempt.
    It is meant to be used within a `with` statement.
    It assumes an area lock on the extent of the flight intent.
    """

    _extent: Volume4D

    _before_oi_refs: List[OperationalIntentReference]
    _before_query: fetch.Query

    _after_oi_refs: List[OperationalIntentReference]
    _after_query: fetch.Query

    _new_oi_ref: Optional[OperationalIntentReference] = None

    def __init__(
        self,
        scenario: TestScenarioType,
        flight_planner: Union[FlightPlanner, FlightPlannerClient],
        dss: DSSInstance,
        extent: Union[Volume4D, List[Volume4D], FlightInfo, List[FlightInfo]],
        orig_oi_ref: Optional[OperationalIntentReference] = None,
    ):
        """
        :param scenario: test scenario in which the operational intent is being validated.
        :param flight_planner: flight planner responsible for maintenance of the operational intent.
        :param dss: DSS instance in which to check for operational intents.
        :param extent: the extent over which the operational intents are to be compared.
        :param orig_oi_ref: if this is validating a previously existing operational intent (e.g. modification), pass the original reference.
        """
        self._scenario: TestScenarioType = scenario
        self._flight_planner: Union[FlightPlanner, FlightPlannerClient] = flight_planner
        self._dss: DSSInstance = dss
        self._orig_oi_ref: Optional[OperationalIntentReference] = orig_oi_ref

        if isinstance(extent, List):
            extents_list: List[Volume4D] = []
            for extent_el in extent:
                if isinstance(extent_el, Volume4D):
                    extents_list.append(extent_el)
                elif isinstance(extent_el, FlightInfo):
                    extents_list.append(
                        extent_el.basic_information.area.bounding_volume.to_f3548v21()
                    )
                else:
                    raise ValueError(f"unexpected extent type {type(extent_el)}")

            self._extent = Volume4DCollection.from_f3548v21(
                extents_list
            ).bounding_volume.to_f3548v21()

        elif isinstance(extent, Volume4D):
            self._extent = extent
        elif isinstance(extent, FlightInfo):
            self._extent = extent.basic_information.area.bounding_volume.to_f3548v21()
        else:
            raise ValueError(f"unexpected extent type {type(extent)}")

    def __enter__(self) -> OpIntentValidator:
        with self._scenario.check("DSS responses", [self._dss.participant_id]) as check:
            try:
                self._before_oi_refs, self._before_query = self._dss.find_op_intent(
                    self._extent
                )
                self._scenario.record_query(self._before_query)
            except QueryError as e:
                self._scenario.record_queries(e.queries)
                self._before_query = e.queries[0]
                check.record_failed(
                    summary="Failed to query DSS for operational intent references before planning request",
                    details=f"Received status code {self._before_query.status_code} from the DSS; {e}",
                    query_timestamps=[self._before_query.request.timestamp],
                )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _find_after_oi(self, oi_id: str) -> Optional[OperationalIntentReference]:
        found = [oi_ref for oi_ref in self._after_oi_refs if oi_ref.id == oi_id]
        return found[0] if len(found) != 0 else None

    def _begin_step_fragment(self):
        with self._scenario.check("DSS responses", [self._dss.participant_id]) as check:
            try:
                self._after_oi_refs, self._after_query = self._dss.find_op_intent(
                    self._extent
                )
                self._scenario.record_query(self._after_query)
            except QueryError as e:
                self._scenario.record_queries(e.queries)
                self._after_query = e.queries[0]
                check.record_failed(
                    summary="Failed to query DSS for operational intent references after planning request",
                    details=f"Received status code {self._after_query.status_code} from the DSS; {e}",
                    query_timestamps=[self._after_query.request.timestamp],
                )

        oi_ids_delta = {oi_ref.id for oi_ref in self._after_oi_refs} - {
            oi_ref.id for oi_ref in self._before_oi_refs
        }

        if (
            len(oi_ids_delta) > 1
        ):  # TODO: could a USS cut up a submitted flight intent into several op intents?
            raise TestRunCannotContinueError(
                f"unexpectedly got more than 1 new operational intent reference after planning request was created (IDs: {oi_ids_delta}): the test scenario might be malformed or some external requests might have interfered"
            )
        if len(oi_ids_delta) == 1:
            self._new_oi_ref = self._find_after_oi(oi_ids_delta.pop())

    def expect_removed(self, oi_id: EntityID) -> None:
        """Validate that a specific operational intent reference was removed from the DSS.

        It implements the test step described in validate_removed_operational_intent.md.
        """
        self._begin_step_fragment()

        with self._scenario.check(
            "Operational intent not shared", self._flight_planner.participant_id
        ) as check:
            if oi_id in [oi_ref.id for oi_ref in self._after_oi_refs]:
                check.record_failed(
                    summary=f"Removed flight's op intent {oi_id} remained shared",
                    details=f"{self._flight_planner.participant_id} should have removed their flight which should include removal of the corresponding operational intent from the interoperability ecosystem, but a reference to operational intent {oi_id} was still found in the DSS after removal",
                    query_timestamps=[
                        self._before_query.request.timestamp,
                        self._after_query.request.timestamp,
                    ],
                )
            if self._new_oi_ref is not None:
                check.record_failed(
                    summary=f"New op intent {self._new_oi_ref.id} was shared",
                    details=f"{self._flight_planner.participant_id} should have removed their flight which should have included removal of the corresponding operational intent from the interoperability ecosystem, but a new operational intent {self._new_oi_ref.id} was created during the time {oi_id} should have been removed",
                    query_timestamps=[
                        self._before_query.request.timestamp,
                        self._after_query.request.timestamp,
                    ],
                )

    def expect_not_shared(self) -> None:
        """Validate that an operational intent information was not shared with the DSS.

        It implements the test step described in validate_not_shared_operational_intent.md.
        """
        self._begin_step_fragment()

        with self._scenario.check(
            "Operational intent not shared", [self._flight_planner.participant_id]
        ) as check:
            if self._new_oi_ref is not None:
                check.record_failed(
                    summary="Operational intent reference was incorrectly shared with DSS",
                    severity=Severity.High,
                    details=f"USS {self._flight_planner.participant_id} was not supposed to share an operational intent with the DSS, but the new operational intent with ID {self._new_oi_ref.id} was found",
                    query_timestamps=[self._after_query.request.timestamp],
                )

    def expect_shared(
        self,
        flight_intent: Union[InjectFlightRequest, FlightInfo],
        skip_if_not_found: bool = False,
    ) -> Optional[OperationalIntentReference]:
        """Validate that operational intent information was correctly shared for a flight intent.

        This function implements the test step described in validate_shared_operational_intent.md.

        :param flight_intent: the flight intent that was supposed to have been shared.
        :param skip_if_not_found: set to True to skip the execution of the checks if the operational intent was not found while it should have been modified.

        :returns: the shared operational intent reference. None if skipped because not found.
        """
        if isinstance(flight_intent, InjectFlightRequest):
            flight_intent = FlightInfo.from_scd_inject_flight_request(flight_intent)

        self._begin_step_fragment()
        oi_ref = self._operational_intent_shared_check(flight_intent, skip_if_not_found)
        if oi_ref is None:
            return None

        self._check_op_intent_reference(flight_intent, oi_ref)
        self._check_op_intent_details(flight_intent, oi_ref)

        # Check telemetry if intent is off-nominal
        if flight_intent.basic_information.uas_state in {
            UasState.OffNominal,
            UasState.Contingent,
        } and self._dss.can_use_scope(
            Scope.ConformanceMonitoringForSituationalAwareness
        ):
            self._check_op_intent_telemetry(oi_ref)

        return oi_ref

    def expect_shared_with_invalid_data(
        self,
        flight_intent: Union[InjectFlightRequest, FlightInfo],
        validation_failure_type: OpIntentValidationFailureType,
        invalid_fields: Optional[List] = None,
        skip_if_not_found: bool = False,
    ) -> Optional[OperationalIntentReference]:
        """Validate that operational intent information was shared with dss,
        but when shared with other USSes, it is expected to have specified invalid data.

        This function implements the test step described in validate_sharing_operational_intent_but_with_invalid_interuss_data.

        :param skip_if_not_found: set to True to skip the execution of the checks if the operational intent was not found while it should have been modified.
        :param validation_failure_type: specific type of validation failure expected
        :param invalid_fields: Optional list of invalid fields to expect when validation_failure_type is OI_DATA_FORMAT

        :returns: the shared operational intent reference. None if skipped because not found.
        """
        if isinstance(flight_intent, InjectFlightRequest):
            flight_intent = FlightInfo.from_scd_inject_flight_request(flight_intent)

        self._begin_step_fragment()
        oi_ref = self._operational_intent_shared_check(flight_intent, skip_if_not_found)
        if oi_ref is None:
            return None

        with self._scenario.check(
            "Operational intent details retrievable",
            [self._flight_planner.participant_id],
        ) as check:
            try:
                goidr_json, oi_full_query = self._dss.get_full_op_intent(
                    oi_ref, self._flight_planner.participant_id
                )
                self._scenario.record_query(oi_full_query)
            except QueryError as e:
                self._scenario.record_queries(e.queries)
                oi_full_query = e.queries[0]
                if oi_full_query.status_code != 200:
                    # fail only if details could not be retrieved, as validation failures are acceptable here
                    check.record_failed(
                        summary="Operational intent details could not be retrieved from USS",
                        details=f"Received status code {oi_full_query.status_code} from {self._flight_planner.participant_id} when querying for details of operational intent {oi_ref.id}; {e}",
                        query_timestamps=[oi_full_query.request.timestamp],
                    )

        validation_failures = self._evaluate_op_intent_validation(oi_full_query)
        expected_validation_failure_found = self._expected_validation_failure_found(
            validation_failures, validation_failure_type, invalid_fields
        )

        # validation errors expected check
        with self._scenario.check(
            "Invalid data in Operational intent details shared by Mock USS for negative test",
            [self._flight_planner.participant_id],
        ) as check:
            if not expected_validation_failure_found:
                check.record_failed(
                    summary="This negative test case requires specific invalid data shared with other USS in Operational intent details ",
                    severity=Severity.High,
                    details=f"Data shared by Mock USS with other USSes did not have the specified invalid data, as expected for test case.",
                    query_timestamps=[oi_full_query.request.timestamp],
                )

        return oi_ref

    def _operational_intent_shared_check(
        self,
        flight_intent: FlightInfo,
        skip_if_not_found: bool,
    ) -> Optional[OperationalIntentReference]:

        with self._scenario.check(
            "Operational intent shared correctly", [self._flight_planner.participant_id]
        ) as check:
            if self._orig_oi_ref is None:
                # We expect a new op intent to have been created. Exception made if skip_if_not_found=True: step is
                # skipped.
                if self._new_oi_ref is None:
                    if not skip_if_not_found:
                        check.record_failed(
                            summary="Operational intent reference not found in DSS",
                            details=f"USS {self._flight_planner.participant_id} was supposed to have shared a new operational intent with the DSS, but no matching operational intent references were found in the DSS in the area of the flight intent",
                            query_timestamps=[self._after_query.request.timestamp],
                        )
                    else:
                        self._scenario.record_note(
                            f"{self._flight_planner.participant_id} no op intent",
                            f"No new operational intent was found in DSS for test step '{self._scenario.current_step_name()}'.",
                        )
                        return None
                oi_ref = self._new_oi_ref

            elif self._new_oi_ref is None:
                # We expect the original op intent to have been either modified or left untouched, thus must be among
                # the returned op intents. If additionally the op intent corresponds to an active flight, we fail a
                # different appropriate check. Exception made if skip_if_not_found=True and op intent was deleted: step
                # is skipped.
                modified_oi_ref = self._find_after_oi(self._orig_oi_ref.id)

                # skip check if skip_if_not_found=True and op intent was deleted
                if modified_oi_ref is None and skip_if_not_found:
                    self._scenario.record_note(
                        f"{self._flight_planner.participant_id} no op intent",
                        f"Operational intent reference with ID {self._orig_oi_ref.id} not found in DSS for test step '{self._scenario.current_step_name()}'.",
                    )
                    check.skip()
                    return None

                # check flight was not deleted if it is active
                if (flight_intent.basic_information.uas_state == UasState.Nominal) and (
                    flight_intent.basic_information.usage_state
                    == AirspaceUsageState.InUse
                ):
                    with self._scenario.check(
                        "Operational intent for active flight not deleted",
                        [self._flight_planner.participant_id],
                    ) as active_flight_check:
                        if modified_oi_ref is None:
                            active_flight_check.record_failed(
                                summary="Operational intent reference for active flight not found in DSS",
                                details=f"USS {self._flight_planner.participant_id} was supposed to have shared with the DSS an updated operational intent by modifying it, but no matching operational intent references were found in the DSS in the area of the flight intent",
                                query_timestamps=[self._after_query.request.timestamp],
                            )

                if modified_oi_ref is None:
                    check.record_failed(
                        summary="Operational intent reference not found in DSS",
                        details=f"USS {self._flight_planner.participant_id} was supposed to have shared with the DSS an updated operational intent by modifying it, but no matching operational intent references were found in the DSS in the area of the flight intent",
                        query_timestamps=[self._after_query.request.timestamp],
                    )
                oi_ref = modified_oi_ref

            else:
                # we expect the original op intent to have been replaced with a new one, thus old one must NOT be among the returned op intents
                if self._find_after_oi(self._orig_oi_ref.id) is not None:
                    check.record_failed(
                        summary="Operational intent reference found duplicated in DSS",
                        details=f"USS {self._flight_planner.participant_id} was supposed to have shared with the DSS an updated operational intent by replacing it, but it ended up duplicating the operational intent in the DSS",
                        query_timestamps=[self._after_query.request.timestamp],
                    )
                oi_ref = self._new_oi_ref

        return oi_ref

    def _check_op_intent_reference(
        self, flight_intent: FlightInfo, oi_ref: OperationalIntentReference
    ):
        with self._scenario.check(
            "Operational intent state is correct",
            [self._flight_planner.participant_id],
        ) as check:
            if flight_intent.get_f3548v21_op_intent_state() != oi_ref.state:
                check.record_failed(
                    summary="Operational intent state does not match user's flight intent",
                    details=f"Expected state {flight_intent.get_f3548v21_op_intent_state()} but got state {oi_ref.state}",
                    query_timestamps=[self._after_query.request.timestamp],
                )

    def _check_op_intent_details(
        self, flight_intent: FlightInfo, oi_ref: OperationalIntentReference
    ):
        with self._scenario.check(
            "Operational intent details retrievable",
            [self._flight_planner.participant_id],
        ) as check:
            try:
                oi_full, oi_full_query = self._dss.get_full_op_intent(
                    oi_ref, self._flight_planner.participant_id
                )
                self._scenario.record_query(oi_full_query)
            except QueryError as e:
                self._scenario.record_queries(e.queries)
                oi_full_query = e.queries[0]
                check.record_failed(
                    summary="Operational intent details could not be retrieved from USS",
                    details=f"Received status code {oi_full_query.status_code} from {self._flight_planner.participant_id} when querying for details of operational intent {oi_ref.id}; {e}",
                    query_timestamps=[oi_full_query.request.timestamp],
                )

        validation_failures = self._evaluate_op_intent_validation(oi_full_query)
        with self._scenario.check(
            "Operational intent details data format",
            [self._flight_planner.participant_id],
        ) as check:
            data_format_fail = (
                self._expected_validation_failure_found(
                    validation_failures, OpIntentValidationFailureType.DataFormat
                )
                if validation_failures
                else None
            )
            if data_format_fail:
                errors = data_format_fail.errors
                check.record_failed(
                    summary="Operational intent details response failed schema validation",
                    severity=Severity.Medium,
                    details="The response received from querying operational intent details failed validation against the required OpenAPI schema:\n"
                    + "\n".join(
                        f"At {e.json_path} in the response: {e.message}" for e in errors
                    ),
                    query_timestamps=[oi_full_query.request.timestamp],
                )

        with self._scenario.check(
            "Correct operational intent details", [self._flight_planner.participant_id]
        ) as check:
            error_text = validate_op_intent_details(
                oi_full.details,
                flight_intent.astm_f3548_21.priority,
                flight_intent.basic_information.area.bounding_volume.to_f3548v21(),
            )
            if error_text:
                check.record_failed(
                    summary="Operational intent details do not match user flight intent",
                    severity=Severity.High,
                    details=error_text,
                    query_timestamps=[oi_full_query.request.timestamp],
                )

        with self._scenario.check(
            "Off-nominal volumes", [self._flight_planner.participant_id]
        ) as check:
            off_nom_vol_fail = (
                self._expected_validation_failure_found(
                    validation_failures,
                    OpIntentValidationFailureType.NominalWithOffNominalVolumes,
                )
                if validation_failures
                else None
            )
            if off_nom_vol_fail:
                check.record_failed(
                    summary="Accepted or Activated operational intents are not allowed off-nominal volumes",
                    severity=Severity.Medium,
                    details=off_nom_vol_fail.error_text,
                    query_timestamps=[oi_full_query.request.timestamp],
                )

        with self._scenario.check(
            "Vertices", [self._flight_planner.participant_id]
        ) as check:
            vertices_fail = (
                self._expected_validation_failure_found(
                    validation_failures, OpIntentValidationFailureType.VertexCount
                )
                if validation_failures
                else None
            )
            if vertices_fail:
                check.record_failed(
                    summary="Too many vertices",
                    severity=Severity.Medium,
                    details=vertices_fail.error_text,
                    query_timestamps=[oi_full_query.request.timestamp],
                )

    def _check_op_intent_telemetry(self, oi_ref: OperationalIntentReference):
        with self._scenario.check(
            "Operational intent telemetry retrievable",
            [self._flight_planner.participant_id],
        ) as check:
            try:
                oi_tel, oi_tel_query = self._dss.get_op_intent_telemetry(
                    oi_ref, self._flight_planner.participant_id
                )
                self._scenario.record_query(oi_tel_query)
            except fetch.QueryError as e:
                self._scenario.record_queries(e.queries)
                oi_tel_query = e.queries[0]
                check.record_failed(
                    summary="Operational intent telemetry could not be retrieved from USS",
                    details=f"Received status code {oi_tel_query.status_code} from {self._flight_planner.participant_id} when querying for telemetry of operational intent {oi_ref.id}; {e}",
                    query_timestamps=[oi_tel_query.request.timestamp],
                )

            if oi_tel is None:
                check.record_failed(
                    summary="Warning (not a failure): USS indicated that no operational intent telemetry was available",
                    severity=Severity.Low,
                    details=f"Received status code {oi_tel_query.status_code} from {self._flight_planner.participant_id} when querying for details of operational intent {oi_ref.id}",
                    query_timestamps=[oi_tel_query.request.timestamp],
                )

    def _evaluate_op_intent_validation(
        self, oi_full_query: fetch.Query
    ) -> Set[OpIntentValidationFailure]:
        """Evaluates the validation failures in operational intent received"""

        validation_failures = set()
        errors = schema_validation.validate(
            schema_validation.F3548_21.OpenAPIPath,
            schema_validation.F3548_21.GetOperationalIntentDetailsResponse,
            oi_full_query.response.json,
        )
        if errors:
            validation_failures.add(
                OpIntentValidationFailure(
                    validation_failure_type=OpIntentValidationFailureType.DataFormat,
                    errors=errors,
                )
            )
        else:
            try:
                goidr = ImplicitDict.parse(
                    oi_full_query.response.json, GetOperationalIntentDetailsResponse
                )
                oi_full = goidr.operational_intent

                if (
                    oi_full.reference.state == OperationalIntentState.Accepted
                    or oi_full.reference.state == OperationalIntentState.Activated
                ) and oi_full.details.get("off_nominal_volumes", None):
                    details = f"Operational intent {oi_full.reference.id} had {len(oi_full.details.off_nominal_volumes)} off-nominal volumes in wrong state - {oi_full.reference.state}"
                    validation_failures.add(
                        OpIntentValidationFailure(
                            validation_failure_type=OpIntentValidationFailureType.NominalWithOffNominalVolumes,
                            error_text=details,
                        )
                    )

                def volume_vertices(v4):
                    if "outline_circle" in v4.volume:
                        return 1
                    if "outline_polygon" in v4.volume:
                        return len(v4.volume.outline_polygon.vertices)

                all_volumes = oi_full.details.get("volumes", []) + oi_full.details.get(
                    "off_nominal_volumes", []
                )
                n_vertices = sum(volume_vertices(v) for v in all_volumes)

                if n_vertices > 10000:
                    details = (
                        f"Operational intent {oi_full.reference.id} had too many total vertices - {n_vertices}",
                    )
                    validation_failures.add(
                        OpIntentValidationFailure(
                            validation_failure_type=OpIntentValidationFailureType.VertexCount,
                            error_text=details,
                        )
                    )
            except (KeyError, ValueError) as e:
                validation_failures.add(
                    OpIntentValidationFailure(
                        validation_failure_type=OpIntentValidationFailureType.DataFormat,
                        error_text=e,
                    )
                )

        return validation_failures

    def _expected_validation_failure_found(
        self,
        validation_failures: Set[OpIntentValidationFailure],
        expected_validation_type: OpIntentValidationFailureType,
        expected_invalid_fields: Optional[List[str]] = None,
    ) -> OpIntentValidationFailure:
        """
        Checks if expected validation type is in validation failures
        Args:
            expected_invalid_fields: If provided with expected_validation_type OI_DATA_FORMAT, check is made for the fields.

        Returns:
            Returns the expected validation failure if found, or else None
        """
        failure_found: OpIntentValidationFailure = None
        for failure in validation_failures:
            if failure.validation_failure_type == expected_validation_type:
                failure_found = failure

        if failure_found:
            if (
                expected_validation_type == OpIntentValidationFailureType.DataFormat
                and expected_invalid_fields
            ):
                errors = failure_found.errors

                def expected_fields_in_errors(
                    fields: List[str],
                    errors: List[schema_validation.ValidationError],
                ) -> bool:
                    all_found = True
                    for field in fields:
                        field_in_error = False
                        for error in errors:
                            if field in error.json_path:
                                field_in_error = True
                                break
                        all_found = all_found and field_in_error
                    return all_found

                if not expected_fields_in_errors(expected_invalid_fields, errors):
                    failure_found = None

        return failure_found


class OpIntentValidationFailureType(str, Enum):
    DataFormat = "DataFormat"
    """The operational intent did not validate against the canonical JSON Schema."""

    NominalWithOffNominalVolumes = "NominalWithOffNominalVolumes"
    """The operational intent was nominal, but it specified off-nominal volumes."""

    VertexCount = "VertexCount"
    """The operational intent had too many vertices."""


class OpIntentValidationFailure(ImplicitDict):
    validation_failure_type: OpIntentValidationFailureType

    error_text: Optional[str] = None
    """Any error_text returned after validation check"""

    errors: Optional[List[schema_validation.ValidationError]] = None
    """Any errors returned after validation check"""

    def __hash__(self):
        return hash((self.validation_failure_type, self.error_text, str(self.errors)))

    def __eq__(self, other):
        if isinstance(other, OpIntentValidationFailure):
            return (
                self.validation_failure_type,
                self.error_text,
                str(self.errors),
            ) == (
                other.validation_failure_type,
                other.error_text,
                str(other.errors),
            )


def set_uss_available(
    scenario: TestScenarioType,
    dss: DSSInstance,
    uss_sub: str,
) -> str:
    """Set the USS availability to 'Available'.

    This function implements the test step fragment described in set_uss_available.md.

    Returns:
        The new version of the USS availability.
    """
    with scenario.check(
        "USS availability successfully set to 'Available'", [dss.participant_id]
    ) as check:
        try:
            availability_version, avail_query = dss.set_uss_availability(
                uss_sub,
                True,
            )
            scenario.record_query(avail_query)
        except QueryError as e:
            scenario.record_queries(e.queries)
            avail_query = e.queries[0]
            check.record_failed(
                summary=f"Availability of USS {uss_sub} could not be set to available",
                details=f"DSS responded code {avail_query.status_code}; {e}",
                query_timestamps=[avail_query.request.timestamp],
            )
    return availability_version


def set_uss_down(
    scenario: TestScenarioType,
    dss: DSSInstance,
    uss_sub: str,
) -> str:
    """Set the USS availability to 'Down'.

    This function implements the test step fragment described in set_uss_down.md.

    Returns:
        The new version of the USS availability.
    """
    with scenario.check(
        "USS availability successfully set to 'Down'", [dss.participant_id]
    ) as check:
        try:
            availability_version, avail_query = dss.set_uss_availability(
                uss_sub,
                False,
            )
            scenario.record_query(avail_query)
        except QueryError as e:
            scenario.record_queries(e.queries)
            avail_query = e.queries[0]
            check.record_failed(
                summary=f"Availability of USS {uss_sub} could not be set to down",
                details=f"DSS responded code {avail_query.status_code}; {e}",
                query_timestamps=[avail_query.request.timestamp],
            )
    return availability_version


def make_dss_report(
    scenario: TestScenarioType,
    dss: DSSInstance,
    exchange: ExchangeRecord,
) -> str:
    """Make a DSS report.

    This function implements the test step fragment described in make_dss_report.md.

    Returns:
        The report ID.
    """
    with scenario.check(
        "DSS report successfully submitted", [dss.participant_id]
    ) as check:
        try:
            report_id, report_query = dss.make_report(exchange)
            scenario.record_query(report_query)
        except QueryError as e:
            scenario.record_queries(e.queries)
            report_query = e.cause
            check.record_failed(
                summary="DSS report could not be submitted",
                details=f"DSS responded code {report_query.status_code}; {e}",
                query_timestamps=[report_query.request.timestamp],
            )

    with scenario.check(
        "DSS returned a valid report ID", [dss.participant_id]
    ) as check:
        if not report_id:
            check.record_failed(
                summary="Submitted DSS report returned no or empty ID",
                details=f"DSS responded code {report_query.status_code} but with no ID for the report",
                query_timestamps=[report_query.request.timestamp],
            )
    return report_id
