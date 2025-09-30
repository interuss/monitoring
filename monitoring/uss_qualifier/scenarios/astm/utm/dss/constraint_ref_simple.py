from datetime import datetime, timedelta

from uas_standards.astm.f3548.v21.api import EntityID
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class CRSimple(TestScenario):
    """
    A scenario that checks that Constraint references cannot be deleted with the incorrect OVN.

    TODO:
     - enrich with test case to mutate with incorrect OVN (planned via #760)
     - enrich with test case to delete with previous OVN (after mutation: add after #760)
    """

    CR_TYPE = register_resource_type(397, "Constraint Reference")

    _dss: DSSInstance

    _cr_id: EntityID

    _expected_manager: str
    _planning_area: PlanningAreaResource
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
            client_identity: Provides the identity of the client that will be used to create the CRs
            planning_area: An Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.
        """
        super().__init__()
        scopes = {Scope.ConstraintManagement: "create and delete constraint references"}
        # This is an UTMClientSession
        self._dss = dss.get_instance(scopes)
        self._pid = [self._dss.participant_id]

        self._cr_id = id_generator.id_factory.make_id(self.CR_TYPE)

        self._expected_manager = client_identity.subject()

        self._planning_area = planning_area

        # TODO #1053: pass proper times dict
        self._planning_area_volume4d = self._planning_area.resolved_volume4d({})

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self._setup_case()

        self.begin_test_case("Deletion requires correct OVN")
        self._step_attempt_delete_missing_ovn()
        self._step_attempt_delete_incorrect_ovn()
        self.end_test_case()

        self.begin_test_case("Mutation requires correct OVN")
        self._step_attempt_mutation_missing_ovn()
        self._step_attempt_mutation_incorrect_ovn()
        self.end_test_case()

        self.end_test_scenario()

    def _step_create_cr(self):
        cr_params = self._planning_area.get_new_constraint_ref_params(
            time_start=datetime.now() - timedelta(seconds=10),
            time_end=datetime.now() + timedelta(minutes=20),
        )

        self.begin_test_step("Create a constraint reference")
        with self.check(
            "Create constraint reference query succeeds",
            self._pid,
        ) as check:
            try:
                new_cr, subs, query = self._dss.put_constraint_ref(
                    cr_id=self._cr_id,
                    extents=cr_params.extents,
                    uss_base_url=self._planning_area.specification.get_base_url(),
                )
                self.record_query(query)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Could not create constraint reference",
                    details=f"Failed to create first constraint reference with error code {qe.cause_status_code}: {qe.msg}",
                    query_timestamps=qe.query_timestamps,
                )
        self.end_test_step()

    def _step_attempt_delete_missing_ovn(self):
        self.begin_test_step("Attempt deletion with missing OVN")

        with self.check(
            "Request to delete CR with empty OVN fails", self._pid
        ) as check:
            try:
                _, _, q = self._dss.delete_constraint_ref(self._cr_id, "")
                self.record_query(q)
                # We don't expect the reach this point:
                check.record_failed(
                    summary="CR Deletion with empty OVN was not expected to succeed",
                    details=f"Was expecting an HTTP 400, 404 or 409 response because of an empty OVN, but got {q.status_code} instead",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code in [400, 404, 409]:
                    # An empty OVN can be seen as:
                    # an incorrect parameter (400), a reference to a non-existing entity (404) as well as a conflict (409)
                    pass
                else:
                    check.record_failed(
                        summary="CR Deletion with empty OVN failed for unexpected reason",
                        details=f"Was expecting an HTTP 400, 404 or 409 response because of an empty OVN, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )

        self.end_test_step()

    def _step_attempt_delete_incorrect_ovn(self):
        self.begin_test_step("Attempt deletion with incorrect OVN")

        with self.check(
            "Request to delete CR with incorrect OVN fails", self._pid
        ) as check:
            try:
                _, _, q = self._dss.delete_constraint_ref(
                    self._cr_id, "ThisIsAnIncorrectOVN"
                )
                self.record_query(q)
                # We don't expect the reach this point:
                check.record_failed(
                    summary="CR Deletion with incorrect OVN was not expected to succeed",
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
                        summary="CR Deletion with incorrect OVN failed for unexpected reason",
                        details=f"Was expecting an HTTP 409 response because of an incorrect OVN, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )

        self.end_test_step()

    def _step_attempt_mutation_missing_ovn(self):
        self.begin_test_step("Attempt mutation with missing OVN")
        cr_params = self._planning_area.get_new_constraint_ref_params(
            time_start=datetime.now() - timedelta(seconds=10),
            time_end=datetime.now() + timedelta(minutes=20),
        )

        with self.check(
            "Request to mutate CR with empty OVN fails", self._pid
        ) as check:
            try:
                _, _, q = self._dss.put_constraint_ref(
                    cr_id=self._cr_id,
                    extents=cr_params.extents,
                    uss_base_url=self._planning_area.specification.get_base_url(),
                    ovn="",
                )
                self.record_query(q)
                # We don't expect the reach this point:
                check.record_failed(
                    summary="CR mutation with empty OVN was not expected to succeed",
                    details=f"Was expecting an HTTP 400, 404 or 409 response because of an empty OVN, but got {q.status_code} instead",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code in [400, 404, 409]:
                    # An empty OVN can be seen as:
                    # an incorrect parameter (400), a reference to a non-existing entity (404) as well as a conflict (409)
                    pass
                else:
                    check.record_failed(
                        summary="CR mutation with empty OVN failed for unexpected reason",
                        details=f"Was expecting an HTTP 400, 404 or 409 response because of an empty OVN, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )

        self.end_test_step()

    def _step_attempt_mutation_incorrect_ovn(self):
        self.begin_test_step("Attempt mutation with incorrect OVN")
        cr_params = self._planning_area.get_new_constraint_ref_params(
            time_start=datetime.now() - timedelta(seconds=10),
            time_end=datetime.now() + timedelta(minutes=20),
        )

        with self.check(
            "Request to mutate CR with incorrect OVN fails", self._pid
        ) as check:
            try:
                _, _, q = self._dss.put_constraint_ref(
                    cr_id=self._cr_id,
                    extents=cr_params.extents,
                    uss_base_url=self._planning_area.specification.get_base_url(),
                    ovn="ThisIsAnIncorrectOVN",
                )
                self.record_query(q)
                # We don't expect the reach this point:
                check.record_failed(
                    summary="CR mutation with incorrect OVN was not expected to succeed",
                    details=f"Was expecting an HTTP 400 or 409 response because of an incorrect OVN, but got {q.status_code} instead",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code in [400, 409]:
                    # An empty OVN cen be seen as both an incorrect parameter as well as a conflict
                    # because the value is incorrect: we accept both a 400 and 409 return code here.
                    pass
                else:
                    check.record_failed(
                        summary="CR mutation with incorrect OVN failed for unexpected reason",
                        details=f"Was expecting an HTTP 400 or 409 response because of an incorrect OVN, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )
        self.end_test_step()

    def _setup_case(self):
        self.begin_test_case("Setup")
        self.begin_test_step("Ensure clean workspace")
        self._ensure_clean_workspace_step()
        self.end_test_step()

        self._step_create_cr()

        self.end_test_case()

    def _ensure_clean_workspace_step(self):
        # Delete any active CR we might own
        test_step_fragments.cleanup_active_constraint_refs(
            self,
            self._dss,
            self._planning_area_volume4d.to_f3548v21(),
            self._expected_manager,
        )

        # Make sure the CR IDs we are going to use are available
        test_step_fragments.cleanup_constraint_ref(self, self._dss, self._cr_id)

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_clean_workspace_step()
        self.end_cleanup()
