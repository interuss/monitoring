from datetime import datetime, timedelta
from typing import Dict, List

from uas_standards.astm.f3548.v21.api import (
    EntityID,
    OperationalIntentReference,
    OperationalIntentState,
    AirspaceConflictResponse,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib import fetch, schema_validation
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.schema_validation import F3548_21
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
    DSSInstance,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    PendingCheck,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class OIRKeyValidation(TestScenario):
    """
    A scenario that checks that Operational Intent references cannot be created or updated
    if the client does not provide all relevant OVNs in the key field.

    Note that this currently only uses Operational intents: constraint references
    will be added at a later stage.
    """

    # We will be using three IDs for the OIRs
    OIR_TYPES = [
        register_resource_type(382, "Operational Intent Reference, starting now"),
        register_resource_type(
            383, "Operational Intent Reference, non-overlapping with the previous one"
        ),
        register_resource_type(
            384, "Operational Intent Reference, overlapping with the two previous ones"
        ),
    ]

    _dss: DSSInstance

    _oir_ids: List[EntityID]

    # Keep track of the current OIR state
    _current_oirs: Dict[EntityID, OperationalIntentReference]

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        client_identity: ClientIdentityResource,
        planning_area: PlanningAreaResource,
    ):
        """
        Args:
            dss: dss to test
            id_generator: will let us generate specific identifiers
            client_identity: Provides the identity of the client that will be used to create the OIRs
            planning_area: An Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.
        """
        super().__init__()
        scopes = {
            Scope.StrategicCoordination: "create and delete operational intent references"
        }
        # This is an UTMClientSession
        self._dss = dss.get_instance(scopes)
        self._pid = [self._dss.participant_id]

        self._oir_ids = [id_generator.id_factory.make_id(t) for t in self.OIR_TYPES]

        self._expected_manager = client_identity.subject()

        self._planning_area = planning_area.specification

        self._planning_area_volume4d = Volume4D(
            volume=self._planning_area.volume,
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self._setup_case()

        self.begin_test_case("Key validation on creation")
        self._steps_create_non_overlapping_oirs()
        self._steps_attempt_create_overlapping_oir()
        self.end_test_case()

        self.begin_test_case("Key validation on mutation")
        self._steps_attempt_mutation_to_cause_overlap()
        self.end_test_case()

        self.end_test_scenario()

    def _steps_create_non_overlapping_oirs(self):
        """Creates two non-overlapping OIRs. They use the same planning area but are separated by time."""

        # First OIR starts in the recent past and extends 20 minutes into the future
        first_oir_params = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.base_url,
            time_start=datetime.now() - timedelta(seconds=10),
            time_end=datetime.now() + timedelta(minutes=20),
            subscription_id=None,
        )

        # The second OIR will be for the same area, but starting one hour after the first one ends
        second_oir_params = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.base_url,
            time_start=datetime.now() + timedelta(hours=1, minutes=20),
            time_end=datetime.now() + timedelta(hours=1, minutes=40),
            subscription_id=None,
        )

        self.begin_test_step("Create first OIR")
        with self.check(
            "First operational intent reference in area creation query succeeds",
            self._pid,
        ) as check:
            try:
                first_oir, subs, query = self._dss.put_op_intent(
                    extents=first_oir_params.extents,
                    key=first_oir_params.key,
                    state=first_oir_params.state,
                    base_url=first_oir_params.uss_base_url,
                    oi_id=self._oir_ids[0],
                )
                self.record_query(query)
                self._current_oirs[first_oir.id] = first_oir
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Could not create first operational intent reference",
                    details=f"Failed to create first operational intent reference with error code {qe.cause_status_code}: {qe.msg}",
                    query_timestamps=qe.query_timestamps,
                )
        self.end_test_step()
        self.begin_test_step("Create second non-overlapping OIR")
        with self.check(
            "Second, non-overlapping operational intent reference creation succeeds",
            self._pid,
        ) as check:
            try:
                second_oir, subs, query = self._dss.put_op_intent(
                    extents=second_oir_params.extents,
                    key=second_oir_params.key,
                    state=second_oir_params.state,
                    base_url=second_oir_params.uss_base_url,
                    oi_id=self._oir_ids[1],
                )
                self.record_query(query)
                self._current_oirs[second_oir.id] = second_oir
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Could not create second non-overlapping operational intent reference",
                    details=f"Failed to create second operational intent reference with error code {qe.cause_status_code}: {qe.msg}",
                    query_timestamps=qe.query_timestamps,
                )
        self.end_test_step()

    def _attempt_creation_expect_conflict(
        self, oir_id: EntityID, oir_params, conflicting_ids: List[EntityID]
    ):
        with self.check(
            "Create operational intent reference with missing OVN fails", self._pid
        ) as check:
            try:
                _, subs, q = self._dss.put_op_intent(
                    extents=oir_params.extents,
                    key=oir_params.key,
                    state=oir_params.state,
                    base_url=oir_params.uss_base_url,
                    oi_id=oir_id,
                )
                self.record_query(q)
                check.record_failed(
                    summary="Operational intent reference with OVN missing in key was created",
                    details=f"Was expecting an HTTP 409 response because of a conflict with OIR {conflicting_ids}, but got a successful response ({q.status_code}) instead",
                    query_timestamps=[q.request.timestamp],
                )
                return
            except QueryError as qe:
                self.record_queries(qe.queries)
                _expect_conflict_code(check, conflicting_ids, qe.cause)
                conflicting_query = qe.cause

        self._validate_conflict_response(conflicting_ids, conflicting_query)

    def _attempt_update_expect_conflict(
        self,
        oir_id: EntityID,
        oir_params,
        conflicting_ids: List[EntityID],
        ovn: EntityID,
    ):
        with self.check(
            "Mutate operational intent reference with missing OVN fails", self._pid
        ) as check:
            try:
                _, subs, q = self._dss.put_op_intent(
                    extents=oir_params.extents,
                    key=oir_params.key,
                    state=oir_params.state,
                    base_url=oir_params.uss_base_url,
                    oi_id=oir_id,
                    ovn=ovn,
                )
                self.record_query(q)
                check.record_failed(
                    summary="Operational intent reference with OVN missing in key was mutated",
                    details=f"Was expecting an HTTP 409 response because of a conflict with OIR {conflicting_ids}, but got a successful response ({q.status_code}) instead",
                    query_timestamps=[q.request.timestamp],
                )
                return
            except QueryError as qe:
                self.record_queries(qe.queries)
                _expect_conflict_code(check, conflicting_ids, qe.cause)
                conflicting_query = qe.cause

        self._validate_conflict_response(conflicting_ids, conflicting_query)

    def _steps_attempt_create_overlapping_oir(self):
        first_oir = self._current_oirs[self._oir_ids[0]]
        second_oir = self._current_oirs[self._oir_ids[1]]

        # ID for the next OIR we will attempt to create
        third_oir_id = self._oir_ids[2]

        conflict_first = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.base_url,
            time_start=first_oir.time_start.value.datetime,
            time_end=first_oir.time_end.value.datetime,
            subscription_id=None,
        )

        self.begin_test_step("Attempt OIR creation overlapping with first OIR")
        self._attempt_creation_expect_conflict(
            third_oir_id, conflict_first, [first_oir.id]
        )
        self.end_test_step()

        conflict_second = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.base_url,
            time_start=second_oir.time_start.value.datetime,
            time_end=second_oir.time_end.value.datetime,
            subscription_id=None,
        )

        self.begin_test_step("Attempt OIR creation overlapping with second OIR")
        self._attempt_creation_expect_conflict(
            third_oir_id, conflict_second, [second_oir.id]
        )
        self.end_test_step()

        conflict_both = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.base_url,
            time_start=first_oir.time_start.value.datetime,
            time_end=second_oir.time_end.value.datetime,
            subscription_id=None,
        )

        self.begin_test_step("Attempt OIR creation overlapping with both OIRs")
        self._attempt_creation_expect_conflict(
            third_oir_id, conflict_both, [first_oir.id, second_oir.id]
        )
        self.end_test_step()

        # Finally, we create the third OIR with the correct key, so we may try to mutate it at the next step
        conflict_both.key = [first_oir.ovn, second_oir.ovn]

        self.begin_test_step("Attempt valid OIR creation overlapping with both OIRs")
        with self.check(
            "Create operational intent reference with proper OVNs succeeds", self._pid
        ) as check:
            try:
                third_oir, subs, q = self._dss.put_op_intent(
                    extents=conflict_both.extents,
                    key=conflict_both.key,
                    state=conflict_both.state,
                    base_url=conflict_both.uss_base_url,
                    oi_id=third_oir_id,
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Could not create operational intent reference with valid parameters",
                    details=f"Failed to create third operational intent reference with error code {qe.cause_status_code}: {qe.msg}",
                    query_timestamps=qe.query_timestamps,
                )
                return
        self.end_test_step()

        self._current_oirs[third_oir.id] = third_oir

    def _validate_conflict_response(
        self, conflicting_ids: List[EntityID], query: fetch.Query
    ):
        """Checks that the conflict response body is as specified.
        If the missing_operational_intents field is defined, its content is checked against the list of passed conflicting ids."""

        with self.check(
            "Failure response due to conflict has proper format", self._pid
        ) as check:
            errors = schema_validation.validate(
                F3548_21.OpenAPIPath,
                F3548_21.AirspaceConflictResponse,
                query.response.json,
            )
            if errors:
                check.record_failed(
                    summary="Conflict response body did not match OpenAPI schema",
                    details=f"The following errors were found: {errors}",
                    query_timestamps=[query.request.timestamp],
                )

        # Expected to succeed if the previous check passed
        parsed_response = query.parse_json_result(AirspaceConflictResponse)

        # The OpenAPI spec does not seem to force implementations to return the missing operational intents:
        # hence we only validate the content of that field if it is provided
        if "missing_operational_intents" in parsed_response:
            with self.check(
                "Failure response due to conflict contains conflicting OIRs", self._pid
            ) as check:
                missing_oir_ids = [
                    o.id for o in parsed_response.missing_operational_intents
                ]
                for expected_conflict_id in conflicting_ids:
                    if expected_conflict_id not in missing_oir_ids:
                        check.record_failed(
                            summary="Expected conflicting OIR ID not in conflict response",
                            details=f"Expected to find OIR ID {expected_conflict_id} in the missing operational intents list, but it was not found",
                            query_timestamps=[query.request.timestamp],
                        )

    def _steps_attempt_mutation_to_cause_overlap(self):
        first_oir = self._current_oirs[self._oir_ids[0]]
        second_oir = self._current_oirs[self._oir_ids[1]]
        # We try to change the base URL, all else remains equal
        oir_to_mutate = self._current_oirs[self._oir_ids[2]]
        change_base_url = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=oir_to_mutate.state,
            uss_base_url=oir_to_mutate.uss_base_url + "/mutated",
            time_start=oir_to_mutate.time_start.value.datetime,
            time_end=oir_to_mutate.time_end.value.datetime,
            subscription_id=None,
        )

        # If both OVns are missing:
        self.begin_test_step("Attempt mutation with both OVNs missing")
        self._attempt_update_expect_conflict(
            oir_to_mutate.id,
            change_base_url,
            [first_oir.id, second_oir.id],
            oir_to_mutate.ovn,
        )
        self.end_test_step()

        # If the first OVN is missing:
        self.begin_test_step("Attempt mutation with first OVN missing")
        change_base_url.key = [second_oir.ovn]
        self._attempt_update_expect_conflict(
            oir_to_mutate.id, change_base_url, [first_oir.id], oir_to_mutate.ovn
        )
        self.end_test_step()

        # Try to overlap only with the first one
        conflict_with_first = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=oir_to_mutate.state,
            uss_base_url=oir_to_mutate.uss_base_url,
            time_start=first_oir.time_start.value.datetime,
            time_end=first_oir.time_end.value.datetime,
            subscription_id=None,
        )

        # We expect to conflict only with the first one
        self.begin_test_step("Attempt mutation to overlap with the first OIR")
        self._attempt_update_expect_conflict(
            oir_to_mutate.id, conflict_with_first, [first_oir.id], oir_to_mutate.ovn
        )
        self.end_test_step()

    def _setup_case(self):
        self.begin_test_case("Setup")
        # Multiple runs of the scenario seem to rely on the same instance of it:
        # thus we need to reset the state of the scenario before running it.
        self._current_oirs = {}
        self.begin_test_step("Ensure clean workspace")
        self._ensure_clean_workspace_step()
        self.end_test_step()
        self.end_test_case()

    def _ensure_clean_workspace_step(self):

        # Delete any active OIR we might own
        test_step_fragments.cleanup_active_oirs(
            self,
            self._dss,
            self._planning_area_volume4d.to_f3548v21(),
            self._expected_manager,
        )

        # Make sure the OIR IDs we are going to use are available
        for oir_id in self._oir_ids:
            test_step_fragments.cleanup_op_intent(self, self._dss, oir_id)

        # Also drop any subs we might own and that could interfere
        test_step_fragments.cleanup_active_subs(
            self, self._dss, self._planning_area_volume4d.to_f3548v21()
        )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_clean_workspace_step()
        self.end_cleanup()


def _expect_conflict_code(
    check: PendingCheck, conflicting_ids: List[EntityID], query: fetch.Query
):
    if query.status_code != 409:
        check.record_failed(
            summary="OIR Creation failed for the unexpected reason",
            details=f"Was expecting an HTTP 409 response because of a conflict with OIR {conflicting_ids}, but got a {query.status_code} instead",
            query_timestamps=[query.request.timestamp],
        )
