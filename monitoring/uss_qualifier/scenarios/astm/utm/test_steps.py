from typing import List

from monitoring.monitorlib import schema_validation, fetch
from monitoring.monitorlib.geotemporal import Volume4DCollection
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    Volume4D,
    OperationalIntentReference,
)

from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    InjectFlightRequest,
)
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlanner,
)
from monitoring.uss_qualifier.scenarios.astm.utm.evaluation import (
    validate_op_intent_details,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


class ValidateNotSharedOperationalIntent(object):
    """Validate that an operational intent information was not shared with the DSS by comparing the operational intents
    found in the area of the flight intent before and after the planning attempt.
    This assumes an area lock on the extent of the flight intent.

    This class is meant to be used within a `with` statement.
    It implements the test step described in validate_not_shared_operational_intent.md.
    """

    _scenario: TestScenarioType
    _flight_planner: FlightPlanner
    _dss: DSSInstance
    _test_step: str

    _flight_intent_extent: Volume4D
    _initial_op_intent_refs: List[OperationalIntentReference]
    _initial_query: fetch.Query

    def __init__(
        self,
        scenario: TestScenarioType,
        flight_planner: FlightPlanner,
        dss: DSSInstance,
        test_step: str,
        flight_intent: InjectFlightRequest,
    ):
        self._scenario = scenario
        self._flight_planner = flight_planner
        self._dss = dss
        self._test_step = test_step

        self._flight_intent_extent = Volume4DCollection.from_f3548v21(
            flight_intent.operational_intent.volumes
            + flight_intent.operational_intent.off_nominal_volumes
        ).bounding_volume.to_f3548v21()

    def __enter__(self):
        self._initial_op_intent_refs, self._initial_query = self._dss.find_op_intent(
            self._flight_intent_extent
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._scenario.record_note(
                self._flight_planner.participant_id,
                f"Exception occurred during ValidateNotSharedOperationalIntent ({exc_type}: {exc_val}).",
            )
            raise exc_val

        self._scenario.begin_test_step(self._test_step)
        self._scenario.record_query(self._initial_query)

        op_intent_refs, query = self._dss.find_op_intent(self._flight_intent_extent)
        self._scenario.record_query(query)

        oi_ids_delta = {oi_ref.id for oi_ref in op_intent_refs} - {
            oi_ref.id for oi_ref in self._initial_op_intent_refs
        }
        with self._scenario.check(
            "Operational intent not shared", [self._flight_planner.participant_id]
        ) as check:
            if len(oi_ids_delta) > 0:
                check.record_failed(
                    summary="Operational intent reference was incorrectly shared with DSS",
                    severity=Severity.High,
                    details=f"USS {self._flight_planner.participant_id} was not supposed to share an operational intent with the DSS, but new operational intent(s) with ID(s) {oi_ids_delta} were found",
                    query_timestamps=[query.request.timestamp],
                )

        self._scenario.end_test_step()


def validate_shared_operational_intent(
    scenario: TestScenarioType,
    flight_planner: FlightPlanner,
    dss: DSSInstance,
    test_step: str,
    flight_intent: InjectFlightRequest,
    op_intent_id: str,
    skip_if_not_found: bool = False,
) -> bool:
    """Validate that operational intent information was correctly shared for a flight intent.

    This function implements the test step described in
    validate_shared_operational_intent.md.

    :returns: True if the operational intent was validated. May return False without failing a check e.g. if the
    operational intent was not found and skip_if_not_found was True.
    """
    scenario.begin_test_step(test_step)
    extent = Volume4DCollection.from_f3548v21(
        flight_intent.operational_intent.volumes
        + flight_intent.operational_intent.off_nominal_volumes
    ).bounding_volume.to_f3548v21()
    op_intent_refs, query = dss.find_op_intent(extent)
    scenario.record_query(query)
    with scenario.check("DSS response", [dss.participant_id]) as check:
        if query.status_code != 200:
            check.record_failed(
                summary="Failed to query DSS for operational intents",
                severity=Severity.High,
                details=f"Received status code {query.status_code} from the DSS",
                query_timestamps=[query.request.timestamp],
            )

    matching_op_intent_refs = [
        op_intent_ref
        for op_intent_ref in op_intent_refs
        if op_intent_ref.id == op_intent_id
    ]
    with scenario.check(
        "Operational intent shared correctly", [flight_planner.participant_id]
    ) as check:
        if not matching_op_intent_refs:
            if not skip_if_not_found:
                check.record_failed(
                    summary="Operational intent reference not found in DSS",
                    severity=Severity.High,
                    details=f"USS {flight_planner.participant_id} was supposed to have shared an operational intent with ID {op_intent_id}, but no operational intent references with that ID were found in the DSS in the area of the flight intent",
                    query_timestamps=[query.request.timestamp],
                )
            else:
                scenario.record_note(
                    flight_planner.participant_id,
                    f"Operational intent reference with ID {op_intent_id} not found in DSS, instructed to skip test step.",
                )
                scenario.end_test_step()
                return False
    op_intent_ref = matching_op_intent_refs[0]

    op_intent, query = dss.get_full_op_intent(op_intent_ref)
    scenario.record_query(query)
    with scenario.check(
        "Operational intent details retrievable", [flight_planner.participant_id]
    ) as check:
        if query.status_code != 200:
            check.record_failed(
                summary="Operational intent details could not be retrieved from USS",
                severity=Severity.High,
                details=f"Received status code {query.status_code} from {flight_planner.participant_id} when querying for details of operational intent {op_intent_id}",
                query_timestamps=[query.request.timestamp],
            )

    with scenario.check(
        "Operational intent details data format", [flight_planner.participant_id]
    ) as check:
        errors = schema_validation.validate(
            schema_validation.F3548_21.OpenAPIPath,
            schema_validation.F3548_21.GetOperationalIntentDetailsResponse,
            query.response.json,
        )
        if errors:
            check.record_failed(
                summary="Operational intent details response failed schema validation",
                severity=Severity.Medium,
                details="The response received from querying operational intent details failed validation against the required OpenAPI schema:\n"
                + "\n".join(
                    f"At {e.json_path} in the response: {e.message}" for e in errors
                ),
                query_timestamps=[query.request.timestamp],
            )

    error_text = validate_op_intent_details(
        op_intent.details, flight_intent.operational_intent.priority, extent
    )
    with scenario.check(
        "Correct operational intent details", [flight_planner.participant_id]
    ) as check:
        if error_text:
            check.record_failed(
                summary="Operational intent details do not match user flight intent",
                severity=Severity.High,
                details=error_text,
                query_timestamps=[query.request.timestamp],
            )

    with scenario.check(
        "Off-nominal volumes", [flight_planner.participant_id]
    ) as check:
        if (
            op_intent.reference.state == OperationalIntentState.Accepted
            or op_intent.reference.state == OperationalIntentState.Activated
        ) and op_intent.details.get("off_nominal_volumes", None):
            check.record_failed(
                summary="Accepted or Activated operational intents are not allowed off-nominal volumes",
                severity=Severity.Medium,
                details=f"Operational intent {op_intent.reference.id} was {op_intent.reference.state} and had {len(op_intent.details.off_nominal_volumes)} off-nominal volumes",
                query_timestamps=[query.request.timestamp],
            )

    all_volumes = op_intent.details.get("volumes", []) + op_intent.details.get(
        "off_nominal_volumes", []
    )

    def volume_vertices(v4):
        if "outline_circle" in v4.volume:
            return 1
        if "outline_polygon" in v4.volume:
            return len(v4.volume.outline_polygon.vertices)

    n_vertices = sum(volume_vertices(v) for v in all_volumes)
    with scenario.check("Vertices", [flight_planner.participant_id]) as check:
        if n_vertices > 10000:
            check.record_failed(
                summary="Too many vertices",
                severity=Severity.Medium,
                details=f"Operational intent {op_intent.reference.id} had {n_vertices} vertices total",
                query_timestamps=[query.request.timestamp],
            )

    scenario.end_test_step()
    return True
