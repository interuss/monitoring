from datetime import datetime, timedelta
from typing import List, Optional

from uas_standards.astm.f3548.v21.api import (
    OperationalIntentReference,
    PutOperationalIntentReferenceParameters,
    EntityID,
    OperationalIntentState,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError, Query
from monitoring.monitorlib.geotemporal import Volume4D, Volume4DCollection
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
    DSSInstancesResource,
    DSSInstance,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.validators.oir_validator import (
    OIRValidator,
    TIME_TOLERANCE_SEC,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    ScenarioCannotContinueError,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class OIRSynchronization(TestScenario):
    """
    A scenario that checks if multiple DSS instances properly synchronize
    operational intent references.

    Not in the scope of the first version of this:
     - access rights (making sure only the manager of the OIR can mutate it)
     - control of the area synchronization (by doing area searches against the secondaries)
     - mutation of an entity on a secondary DSS when it was created on the primary
     - deletion of an entity on a secondary DSS when it was created on the primary
    """

    SUB_TYPE = register_resource_type(
        385, "Operational Intent Reference for synchronization checks"
    )

    _dss: DSSInstance

    _dss_read_instances: List[DSSInstance]

    # Base identifier for the OIR that will be created
    _oir_id: EntityID

    # Base parameters used for OIR creation
    _oir_params: PutOperationalIntentReferenceParameters

    # Keep track of the current OIR state
    _current_oir: Optional[OperationalIntentReference]

    _expected_manager: str

    def __init__(
        self,
        dss: DSSInstanceResource,
        other_instances: DSSInstancesResource,
        id_generator: IDGeneratorResource,
        client_identity: ClientIdentityResource,
        planning_area: PlanningAreaResource,
    ):
        """
        Args:
            dss: dss to test
            other_instances: dss instances to be checked for proper synchronization
            id_generator: will let us generate specific identifiers
            client_identity: tells us the identity we should expect as an entity's manager
            planning_area: An Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.

        """
        super().__init__()
        scopes_primary = {
            Scope.StrategicCoordination: "create and delete operational intent references"
        }
        scopes_read = {Scope.StrategicCoordination: "read operational intents"}

        self._dss = dss.get_instance(scopes_primary)
        self._primary_pid = self._dss.participant_id

        self._dss_read_instances = [
            sec_dss.get_instance(scopes_read)
            for sec_dss in other_instances.dss_instances
        ]

        self._oir_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._expected_manager = client_identity.subject()
        self._planning_area = planning_area.specification

        # Build a ready-to-use 4D volume with no specified time for searching
        # the currently active OIRs
        self._planning_area_volume4d = Volume4D(
            volume=self._planning_area.volume,
        )

        self._oir_params = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.base_url,
            time_start=datetime.now() - timedelta(seconds=10),
            time_end=datetime.now() + timedelta(minutes=20),
            subscription_id=None,
            implicit_sub_base_url=None,
            implicit_sub_for_constraints=None,
        )

    def run(self, context: ExecutionContext):

        # Check that we actually have at least one other DSS to test against:
        if not self._dss_read_instances:
            raise ScenarioCannotContinueError(
                "Cannot run OIRSynchronization scenario: no other DSS instances to test against"
            )

        self.begin_test_scenario(context)
        self._setup_case()
        self.begin_test_case("OIR synchronization")

        self.begin_test_step("Create OIR validation")
        self._create_oir_with_params(self._oir_params)
        self.end_test_step()

        self.begin_test_step("Retrieve newly created OIR")
        self._query_secondaries_and_compare(
            "Newly created OIR can be consistently retrieved from all DSS instances",
            self._oir_params,
        )
        self.end_test_step()

        self.begin_test_step("Search for newly created OIR")
        self._search_secondaries_and_compare(
            "Newly created OIR can be consistently searched for from all DSS instances",
            self._oir_params,
        )
        self.end_test_step()

        self.begin_test_step("Mutate OIR")
        self._test_mutate_oir_shift_time()
        self.end_test_step()

        self.begin_test_step("Retrieve updated OIR")
        self._query_secondaries_and_compare(
            "Updated OIR can be consistently retrieved from all DSS instances",
            self._oir_params,
        )
        self.end_test_step()

        self.begin_test_step("Search for updated OIR")
        self._search_secondaries_and_compare(
            "Updated OIR can be consistently searched for from all DSS instances",
            self._oir_params,
        )
        self.end_test_step()

        self.begin_test_step("Delete OIR")
        self._test_delete_sub()
        self.end_test_step()

        self.begin_test_step("Query deleted OIR")
        self._test_get_deleted_oir()
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")
        # Multiple runs of the scenario seem to rely on the same instance of it:
        # thus we need to reset the state of the scenario before running it.
        self._current_oir = None
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

        # Make sure the OIR ID we are going to use is available
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        # Start by dropping any active subs we might own and that could interfere
        test_step_fragments.cleanup_active_subs(
            self, self._dss, self._planning_area_volume4d.to_f3548v21()
        )

    def _create_oir_with_params(
        self, creation_params: PutOperationalIntentReferenceParameters
    ):

        with self.check(
            "Create operational intent reference query succeeds", [self._primary_pid]
        ) as check:
            try:
                oir, subs, q = self._dss.put_op_intent(
                    extents=creation_params.extents,
                    key=creation_params.key,
                    state=creation_params.state,
                    base_url=creation_params.uss_base_url,
                    oi_id=self._oir_id,
                    ovn=None,
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Create operational intent reference failed",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )
                return

        with self.check(
            "Create operational intent reference response content is correct",
            [self._primary_pid],
        ) as check:
            OIRValidator(
                main_check=check,
                scenario=self,
                expected_manager=self._expected_manager,
                participant_id=[self._primary_pid],
                oir_params=creation_params,
            ).validate_created_oir(self._oir_id, new_oir=q)

        self._current_oir = oir

    def _query_secondaries_and_compare(
        self,
        main_check_name: str,
        expected_oir_params: PutOperationalIntentReferenceParameters,
    ):
        for secondary_dss in self._dss_read_instances:
            with self.check(
                "Get operational intent reference by ID",
                secondary_dss.participant_id,
            ) as check:
                try:
                    oir, q = secondary_dss.get_op_intent_reference(self._oir_id)
                    self.record_query(q)
                except QueryError as qe:
                    self.record_queries(qe.queries)
                    check.record_failed(
                        summary="GET for operational intent reference failed",
                        details=f"Query for operational intent reference failed: {qe.msg}",
                        query_timestamps=qe.query_timestamps,
                    )

            involved_participants = list(
                {self._primary_pid, secondary_dss.participant_id}
            )

            with self.check(
                "Operational intent reference can be found at every DSS",
                involved_participants,
            ) as check:
                if q.status_code != 200:
                    check.record_failed(
                        summary="Requested operational intent was not found at secondary DSS.",
                        details=f"Query for operational intent reference {self._oir_id} failed: {q.msg}",
                        query_timestamps=[q.request.timestamp],
                    )

            self._validate_oir_from_secondary(
                oir=oir,
                q=q,
                expected_oir_params=expected_oir_params,
                main_check_name=main_check_name,
                involved_participants=involved_participants,
            )

    def _search_secondaries_and_compare(
        self,
        main_check_name: str,
        expected_oir_params: PutOperationalIntentReferenceParameters,
    ):
        """
        Returns:
         True if all checks passed, False otherwise; the participant IDs if the checks did not pass.
        """
        for secondary_dss in self._dss_read_instances:
            with self.check(
                "Successful operational intent reference search query",
                [secondary_dss.participant_id],
            ) as check:
                try:
                    oirs, q = secondary_dss.find_op_intent(self._planning_area_volume4d)
                    self.record_query(q)
                except QueryError as qe:
                    self.record_queries(qe.queries)
                    check.record_failed(
                        summary="Failed to search for operational intent references",
                        details=f"Failed to query operational intent references: got response code {qe.cause_status_code}: {qe.msg}",
                        query_timestamps=qe.query_timestamps,
                    )

            involved_participants = list(
                {self._primary_pid, secondary_dss.participant_id}
            )

            with self.check(
                "Propagated operational intent reference general area is synchronized",
                involved_participants,
            ) as check:
                oir: Optional[OperationalIntentReference] = None
                for _oir in oirs:
                    if _oir.id == self._oir_id:
                        oir = _oir
                        break

                if oir is None:
                    check.record_failed(
                        summary="Propagated OIR not found",
                        details=f"OIR {self._oir_id} was not found in the secondary DSS when searched for its expected geo-temporal extent",
                        query_timestamps=[q.request.timestamp],
                    )

            self._validate_oir_from_secondary(
                oir=oir,
                q=q,
                expected_oir_params=expected_oir_params,
                main_check_name=main_check_name,
                involved_participants=involved_participants,
            )

            # TODO: craft a search with an area of interest that does not intersect with the planning area,
            #  but whose convex hull intersects with the planning area

    def _validate_oir_from_secondary(
        self,
        oir: OperationalIntentReference,
        q: Query,
        expected_oir_params: PutOperationalIntentReferenceParameters,
        main_check_name: str,
        involved_participants: List[str],
    ):

        # TODO: this main check mechanism may be removed if we are able to specify requirements to be validated in test step fragments

        with self.check(main_check_name, involved_participants) as main_check:
            with self.check(
                "Propagated operational intent reference contains the correct manager",
                involved_participants,
            ) as check:
                if oir.manager != self._expected_manager:
                    check_args = dict(
                        summary="Propagated OIR has an incorrect manager",
                        details=f"Expected: {self._expected_manager}, Received: {oir.manager}",
                        query_timestamps=[q.request.timestamp],
                    )
                    check.record_failed(**check_args)
                    main_check.record_failed(**check_args)

            with self.check(
                "Propagated operational intent reference contains the correct USS base URL",
                involved_participants,
            ) as check:
                if oir.uss_base_url != expected_oir_params.uss_base_url:
                    check_args = dict(
                        summary="Propagated OIR has an incorrect USS base URL",
                        details=f"Expected: {expected_oir_params.base_url}, Received: {oir.uss_base_url}",
                        query_timestamps=[q.request.timestamp],
                    )
                    check.record_failed(**check_args)
                    main_check.record_failed(**check_args)

            with self.check(
                "Propagated operational intent reference contains the correct state",
                involved_participants,
            ) as check:
                if oir.state != expected_oir_params.state:
                    check_args = dict(
                        summary="Propagated OIR has an incorrect state",
                        details=f"Expected: {expected_oir_params.state}, Received: {oir.state}",
                        query_timestamps=[q.request.timestamp],
                    )
                    check.record_failed(**check_args)
                    main_check.record_failed(**check_args)

            expected_volume_collection = Volume4DCollection.from_interuss_scd_api(
                expected_oir_params.extents
            )
            expected_end = expected_volume_collection.time_end.datetime
            expected_start = expected_volume_collection.time_start.datetime
            with self.check(
                "Propagated operational intent reference contains the correct start time",
                involved_participants,
            ) as check:
                if (
                    abs(oir.time_start.value.datetime - expected_start).total_seconds()
                    > TIME_TOLERANCE_SEC
                ):
                    check_args = dict(
                        summary="Propagated OIR has an incorrect start time",
                        details=f"Expected: {expected_start}, Received: {oir.time_start}",
                        query_timestamps=[q.request.timestamp],
                    )
                    check.record_failed(**check_args)
                    main_check.record_failed(**check_args)

            with self.check(
                "Propagated operational intent reference contains the correct end time",
                involved_participants,
            ) as check:
                if (
                    abs(oir.time_end.value.datetime - expected_end).total_seconds()
                    > TIME_TOLERANCE_SEC
                ):
                    check_args = dict(
                        summary="Propagated OIR has an incorrect end time",
                        details=f"Expected: {expected_end}, Received: {oir.time_end}",
                        query_timestamps=[q.request.timestamp],
                    )
                    check.record_failed(**check_args)
                    main_check.record_failed(**check_args)

    def _test_mutate_oir_shift_time(self):
        """Mutate the OIR by adding 10 seconds to its start and end times.
        This is achieved by updating the first and last element of the extents.
        """

        new_extents = (
            Volume4DCollection.from_f3548v21(self._oir_params.extents)
            .offset_times(timedelta(seconds=10))
            .to_f3548v21()
        )

        self._oir_params = PutOperationalIntentReferenceParameters(
            extents=new_extents,
            key=self._oir_params.key + [self._current_oir.ovn],
            state=self._oir_params.state,
            uss_base_url=self._oir_params.uss_base_url,
            subscription_id=self._current_oir.subscription_id,
        )

        with self.check(
            "Mutate operational intent reference query succeeds", [self._primary_pid]
        ) as check:
            try:
                oir, subs, q = self._dss.put_op_intent(
                    extents=self._oir_params.extents,
                    key=self._oir_params.key,
                    state=self._oir_params.state,
                    base_url=self._oir_params.uss_base_url,
                    oi_id=self._oir_id,
                    ovn=self._current_oir.ovn,
                    subscription_id=self._oir_params.subscription_id,
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Operational intent reference mutation failed",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )

        with self.check(
            "Mutate operational intent reference response content is correct",
            [self._primary_pid],
        ) as check:
            OIRValidator(
                main_check=check,
                scenario=self,
                expected_manager=self._expected_manager,
                participant_id=[self._primary_pid],
                oir_params=self._oir_params,
            ).validate_mutated_oir(
                expected_oir_id=self._oir_id,
                mutated_oir=q,
                previous_ovn=self._current_oir.ovn,
                previous_version=self._current_oir.version,
            )

        self._current_oir = oir

    def _test_delete_sub(self):
        with self.check(
            "Delete operational intent reference query succeeds", [self._primary_pid]
        ) as check:
            try:
                oir, subs, q = self._dss.delete_op_intent(
                    self._oir_id, self._current_oir.ovn
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Operational intent reference deletion on primary DSS failed",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )

        with self.check(
            "Delete operational intent reference response content is correct",
            [self._primary_pid],
        ) as check:
            OIRValidator(
                main_check=check,
                scenario=self,
                expected_manager=self._expected_manager,
                participant_id=[self._primary_pid],
                oir_params=self._oir_params,
            ).validate_deleted_oir(
                expected_oir_id=self._oir_id,
                deleted_oir=q,
                expected_ovn=self._current_oir.ovn,
                expected_version=self._current_oir.version,
            )

        self._current_oir = None

    def _test_get_deleted_oir(self):
        for secondary_dss in self._dss_read_instances:
            self._confirm_secondary_has_no_oir(secondary_dss)

    def _confirm_secondary_has_no_oir(self, secondary_dss: DSSInstance):
        with self.check(
            "Get operational intent reference by ID",
            secondary_dss.participant_id,
        ) as check:
            try:
                oir, q = secondary_dss.get_op_intent_reference(self._oir_id)
                self.record_query(q)
            except QueryError as qe:
                q = qe.cause
                self.record_query(q)
                if q.status_code != 404:
                    check.record_failed(
                        summary="GET for operational intent reference failed",
                        details=f"Query for operational intent reference failed: {qe.msg}",
                        query_timestamps=qe.query_timestamps,
                    )

        with self.check(
            "Deleted OIR cannot be retrieved from all DSS instances",
            [self._primary_pid, secondary_dss.participant_id],
        ) as check:
            if q.status_code != 404:
                check.record_failed(
                    summary="Secondary DSS still has the deleted operational intent reference",
                    details=f"Expected 404, received {q.status_code}",
                    query_timestamps=[q.request.timestamp],
                )

        with self.check(
            "Successful operational intent reference search query",
            [secondary_dss.participant_id],
        ) as check:
            try:
                oirs, q = secondary_dss.find_op_intent(self._planning_area_volume4d)
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Failed to search for operational intent references",
                    details=f"Failed to query operational intent references: got response code {qe.cause_status_code}: {qe.msg}",
                    query_timestamps=qe.query_timestamps,
                )

        with self.check(
            "Deleted OIR cannot be searched for from all DSS instances",
            [self._primary_pid, secondary_dss.participant_id],
        ) as check:
            if self._oir_id in oirs:
                check.record_failed(
                    summary="Secondary DSS still has the deleted operational intent reference",
                    details=f"OIR {self._oir_id} was found in the secondary DSS when searched for its expected geo-temporal extent",
                    query_timestamps=[q.request.timestamp],
                )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_clean_workspace_step()
        self.end_cleanup()
