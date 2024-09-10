from datetime import datetime, timedelta
from typing import Optional

from uas_standards.astm.f3548.v21.api import (
    EntityID,
    OperationalIntentReference,
    OperationalIntentState,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
    DSSInstance,
)
from monitoring.uss_qualifier.resources.astm.f3548.v21.planning_area import (
    PlanningAreaSpecification,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class OIRSimple(TestScenario):
    """
    A scenario that checks that Operational Intent references cannot be deleted with the incorrect OVN.

    TODO:
     - enrich with test case to mutate with incorrect OVN (planned via #760)
     - enrich with test case to delete with previous OVN (after mutation: add after #760)
    """

    OIR_TYPE = register_resource_type(396, "Operational Intent Reference")

    _dss: DSSInstance

    _oir_id: EntityID

    # Keep track of the current OIR state
    _current_oir: Optional[OperationalIntentReference]
    _expected_manager: str
    _planning_area: PlanningAreaSpecification
    _planning_area_volume4d: Volume4D

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

        self._oir_id = id_generator.id_factory.make_id(self.OIR_TYPE)

        self._expected_manager = client_identity.subject()

        self._planning_area = planning_area.specification

        self._planning_area_volume4d = Volume4D(
            volume=self._planning_area.volume,
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self._setup_case()

        self.begin_test_case("Deletion requires correct OVN")
        self._step_attempt_delete_missing_ovn()
        self._step_attempt_delete_incorrect_ovn()
        self.end_test_case()

        self.end_test_scenario()

    def _step_create_oir(self):
        oir_params = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.base_url,
            time_start=datetime.now() - timedelta(seconds=10),
            time_end=datetime.now() + timedelta(minutes=20),
            subscription_id=None,
        )

        self.begin_test_step("Create an operational intent reference")
        with self.check(
            "Create operational intent reference query succeeds",
            self._pid,
        ) as check:
            try:
                new_oir, subs, query = self._dss.put_op_intent(
                    extents=oir_params.extents,
                    key=oir_params.key,
                    state=oir_params.state,
                    base_url=oir_params.uss_base_url,
                    oi_id=self._oir_id,
                )
                self.record_query(query)
                self._current_oir = new_oir
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Could not create operational intent reference",
                    details=f"Failed to create operational intent reference with error code {qe.cause_status_code}: {qe.msg}",
                    query_timestamps=qe.query_timestamps,
                )
        self.end_test_step()

    def _step_attempt_delete_missing_ovn(self):

        self.begin_test_step("Attempt deletion with missing OVN")

        with self.check(
            "Request to delete OIR with empty OVN fails", self._pid
        ) as check:
            try:
                _, _, q = self._dss.delete_op_intent(self._oir_id, "")
                self.record_query(q)
                # We don't expect the reach this point:
                check.record_failed(
                    summary="OIR Deletion with empty OVN was not expected to succeed",
                    details=f"Was expecting an HTTP 400 or 409 response because of an empty OVN, but got {q.status_code} instead",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code in [400 or 409]:
                    # An empty OVN cen be seen as both an incorrect parameter as well as a conflict
                    # because the value is incorrect: we accept both a 400 and 409 return code here.
                    pass
                else:
                    check.record_failed(
                        summary="OIR Deletion with empty OVN failed for unexpected reason",
                        details=f"Was expecting an HTTP 400 or 409 response because of an empty OVN, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )

        self.end_test_step()

    def _step_attempt_delete_incorrect_ovn(self):

        self.begin_test_step("Attempt deletion with incorrect OVN")

        with self.check(
            "Request to delete OIR with incorrect OVN fails", self._pid
        ) as check:
            try:
                _, _, q = self._dss.delete_op_intent(
                    self._oir_id, "ThisIsAnIncorrectOVN"
                )
                self.record_query(q)
                # We don't expect the reach this point:
                check.record_failed(
                    summary="OIR Deletion with incorrect OVN was not expected to succeed",
                    details=f"Was expecting an HTTP 409 response because of an incorrect OVN, but got {q.status_code} instead",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code == 409:
                    # The spec explicitly requests a 409 response code for incorrect OVNs.
                    pass
                else:
                    check.record_failed(
                        summary="OIR Deletion with incorrect OVN failed for unexpected reason",
                        details=f"Was expecting an HTTP 409 response because of an incorrect OVN, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )

        self.end_test_step()

    def _setup_case(self):
        self.begin_test_case("Setup")
        # Multiple runs of the scenario seem to rely on the same instance of it:
        # thus we need to reset the state of the scenario before running it.
        self._current_oir = None
        self.begin_test_step("Ensure clean workspace")
        self._ensure_clean_workspace_step()
        self.end_test_step()

        self._step_create_oir()

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
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)

        # Also drop any subs we might own and that could interfere
        test_step_fragments.cleanup_active_subs(
            self, self._dss, self._planning_area_volume4d.to_f3548v21()
        )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_clean_workspace_step()
        self.end_cleanup()
