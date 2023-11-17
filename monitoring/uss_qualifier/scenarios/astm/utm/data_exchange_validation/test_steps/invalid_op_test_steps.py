from typing import Optional, Tuple
from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    OperationalIntentReference,
    GetOperationalIntentDetailsResponse,
)
from loguru import logger
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightRequest,
    InjectFlightResponse,
)
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlannerClient,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import OpIntentValidator
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    submit_flight,
    expect_flight_intent_state,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.clients.flight_planning.planning import (
    PlanningActivityResponse,
    PlanningActivityResult,
    FlightPlanStatus,
)


def plan_flight_intent_expect_failed(
    scenario: TestScenarioType,
    test_step: str,
    flight_planner: FlightPlannerClient,
    flight_intent: FlightInfo,
) -> Tuple[PlanningActivityResponse, Optional[str]]:
    """Attempt to plan a flight intent that would result in a Failed result.

    This function implements the test step described in scd_data_exchange_validation.md.
    It validates requirement astm.f3548.v21.SCD00abc.

    Returns: The injection response.
    """

    return submit_flight(
        scenario,
        test_step,
        "Plan should fail",
        {(PlanningActivityResult.Failed, FlightPlanStatus.NotPlanned)},
        {},
        flight_planner,
        flight_intent,
    )


class InvalidOpIntentSharingValidator(OpIntentValidator):
    def expect_shared_with_invalid_data(
        self, flight_intent: InjectFlightRequest, skip_if_not_found: bool = False
    ) -> Optional[OperationalIntentReference]:
        """Validate that operational intent information was shared with dss for a flight intent, but shared invalid data with USS.

        This function implements the test step described in validate_sharing_operational_intent_but_with_invalid_interuss_data.

        :param flight_intent: the flight intent that was supposed to have been shared.
        :param skip_if_not_found: set to True to skip the execution of the checks if the operational intent was not found while it should have been modified.

        :returns: the shared operational intent reference. None if skipped because not found.
        """
        self._begin_step()

        with self._scenario.check(
            "Operational intent shared with DSS", [self._flight_planner.participant_id]
        ) as check:
            if self._orig_oi_ref is None:
                # we expect a new op intent to have been created
                if self._new_oi_ref is None:
                    check.record_failed(
                        summary="Operational intent reference not found in DSS",
                        severity=Severity.High,
                        details=f"USS {self._flight_planner.participant_id} was supposed to have shared a new operational intent with the DSS, but no matching operational intent references were found in the DSS in the area of the flight intent",
                        query_timestamps=[self._after_query.request.timestamp],
                    )
                oi_ref = self._new_oi_ref

            elif self._new_oi_ref is None:
                # We expect the original op intent to have been either modified or left untouched, thus must be among
                # the returned op intents. If additionally the op intent corresponds to an active flight, we fail a
                # different appropriate check. Exception made if skip_if_not_found=True and op intent was deleted: step
                # is skipped.
                modified_oi_ref = self._find_after_oi(self._orig_oi_ref.id)
                if modified_oi_ref is None:
                    if not skip_if_not_found:
                        if (
                            flight_intent.operational_intent.state
                            == OperationalIntentState.Activated
                        ):
                            with self._scenario.check(
                                "Operational intent for active flight not deleted",
                                [self._flight_planner.participant_id],
                            ) as active_flight_check:
                                active_flight_check.record_failed(
                                    summary="Operational intent reference for active flight not found in DSS",
                                    severity=Severity.High,
                                    details=f"USS {self._flight_planner.participant_id} was supposed to have shared with the DSS an updated operational intent by modifying it, but no matching operational intent references were found in the DSS in the area of the flight intent",
                                    query_timestamps=[
                                        self._after_query.request.timestamp
                                    ],
                                )
                        else:
                            check.record_failed(
                                summary="Operational intent reference not found in DSS",
                                severity=Severity.High,
                                details=f"USS {self._flight_planner.participant_id} was supposed to have shared with the DSS an updated operational intent by modifying it, but no matching operational intent references were found in the DSS in the area of the flight intent",
                                query_timestamps=[self._after_query.request.timestamp],
                            )
                    else:
                        self._scenario.record_note(
                            self._flight_planner.participant_id,
                            f"Operational intent reference with ID {self._orig_oi_ref.id} not found in DSS, instructed to skip test step.",
                        )
                        self._scenario.end_test_step()
                        return None
                oi_ref = modified_oi_ref

            else:
                # we expect the original op intent to have been replaced with a new one, thus old one must NOT be among the returned op intents
                if self._find_after_oi(self._orig_oi_ref.id) is not None:
                    check.record_failed(
                        summary="Operational intent reference found duplicated in DSS",
                        severity=Severity.High,
                        details=f"USS {self._flight_planner.participant_id} was supposed to have shared with the DSS an updated operational intent by replacing it, but it ended up duplicating the operational intent in the DSS",
                        query_timestamps=[self._after_query.request.timestamp],
                    )
                oi_ref = self._new_oi_ref

        goidr_json, oi_full_query = self._dss.get_full_op_intent_without_validation(
            oi_ref
        )
        self._scenario.record_query(oi_full_query)
        with self._scenario.check(
            "Operational intent details retrievable",
            [self._flight_planner.participant_id],
        ) as check:
            if oi_full_query.status_code != 200:
                check.record_failed(
                    summary="Operational intent details could not be retrieved from USS",
                    severity=Severity.High,
                    details=f"Received status code {oi_full_query.status_code} from {self._flight_planner.participant_id} when querying for details of operational intent {oi_ref.id}",
                    query_timestamps=[oi_full_query.request.timestamp],
                )

        # if schema validation errors or standard req validation
        with self._scenario.check(
            "Invalid data in Operational intent details shared by Mock USS for negative test",
            [self._flight_planner.participant_id],
        ) as check:

            validation_errors = []
            # schema_validation_errors = schema_validation.validate(
            #     schema_validation.F3548_21.OpenAPIPath,
            #     schema_validation.F3548_21.GetOperationalIntentDetailsResponse,
            #     oi_full_query.response.json,
            # )
            schema_validation_errors = None
            logger.debug(f"Schema validation errors {schema_validation_errors}")
            if schema_validation_errors:
                details = (
                    "The response received from querying operational intent details failed validation against the required OpenAPI schema:\n"
                    + "\n".join(
                        f"At {e.json_path} in the response: {e.message}"
                        for e in schema_validation_errors
                    )
                )
                validation_errors.append(details)
            else:
                oi_full = None
                try:
                    goidr = ImplicitDict.parse(
                        goidr_json, GetOperationalIntentDetailsResponse
                    )
                    oi_full = goidr.operational_intent

                    if (
                        oi_full.reference.state == OperationalIntentState.Accepted
                        or oi_full.reference.state == OperationalIntentState.Activated
                    ) and oi_full.details.get("off_nominal_volumes", None):
                        details = f"Operational intent {oi_full.reference.id} had {len(oi_full.details.off_nominal_volumes)} off-nominal volumes in wrong state - {oi_full.reference.state}"
                        validation_errors.append(details)

                    def volume_vertices(v4):
                        if "outline_circle" in v4.volume:
                            return 1
                        if "outline_polygon" in v4.volume:
                            return len(v4.volume.outline_polygon.vertices)

                    all_volumes = oi_full.details.get(
                        "volumes", []
                    ) + oi_full.details.get("off_nominal_volumes", [])
                    n_vertices = sum(volume_vertices(v) for v in all_volumes)

                    if n_vertices > 10000:
                        details = (
                            f"Operational intent {oi_full.reference.id} had too many total vertices - {n_vertices}",
                        )
                        validation_errors.append(details)
                except (KeyError, ValueError) as e:
                    logger.debug(
                        f"Validation error in GetOperationalIntentDetailsResponse. {e}"
                    )
                    validation_errors.append(e)

            if not validation_errors:
                check.record_failed(
                    summary="This negative test case requires invalid data shared with other USS in Operational intent details ",
                    severity=Severity.High,
                    details=f"Data shared by Mock USS with other USSes had no invalid data. This test case required invalid data for testing.",
                    query_timestamps=[oi_full_query.request.timestamp],
                )

        self._scenario.end_test_step()
        return oi_ref
