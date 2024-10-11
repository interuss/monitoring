from datetime import datetime, timedelta
from typing import Optional

from uas_standards.astm.f3548.v21.api import (
    EntityID,
    OperationalIntentReference,
    OperationalIntentState,
    PutOperationalIntentReferenceParameters,
    Subscription,
    SubscriptionID,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.astm.f3548.v21.planning_area import (
    PlanningAreaSpecification,
)
from monitoring.uss_qualifier.resources.astm.f3548.v21.subscription_params import (
    SubscriptionParams,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class OIRSimple(TestScenario):
    """
    A scenario that checks that Operational Intent references cannot be deleted with the incorrect OVN.

    TODO:
     - enrich with test case to mutate with incorrect OVN (planned via #760)
     - enrich with test case to delete with previous OVN (after mutation: add after #760)
    """

    OIR_TYPE = register_resource_type(396, "Operational Intent Reference")
    SUB_TYPE = register_resource_type(401, "Subscription")
    EXTRA_SUB_TYPE = register_resource_type(402, "Subscription")
    _dss: DSSInstance

    _oir_id: EntityID
    _sub_id: SubscriptionID
    _extra_sub_id: SubscriptionID

    # Keep track of the current OIR state
    _current_oir: Optional[OperationalIntentReference]
    _expected_manager: str
    _planning_area: PlanningAreaSpecification
    _planning_area_volume4d: Volume4D

    # Keep track of the current subscription
    _sub_params: Optional[SubscriptionParams]
    _current_sub: Optional[Subscription]

    _current_extra_sub: Optional[Subscription]

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
        self._sub_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._extra_sub_id = id_generator.id_factory.make_id(self.EXTRA_SUB_TYPE)

        self._expected_manager = client_identity.subject()

        self._planning_area = planning_area.specification

        self._planning_area_volume4d = Volume4D(
            volume=self._planning_area.volume,
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.begin_test_case("Setup")
        self._ensure_clean_workspace()
        self.end_test_case()

        self.begin_test_case("Create and Delete OIR")
        self._step_create_oir()
        # This is an explicit deletion test (not a cleanup)
        self._step_delete_oir(is_cleanup=False)
        self.end_test_case()

        self.begin_test_case("Validate explicit subscription on OIR creation")
        self._setup_case(create_oir=False, create_explicit_sub=True)
        self._step_create_oir_insufficient_subscription()
        self._step_create_oir_sufficient_subscription()
        self.end_test_case()

        self.begin_test_case(
            "Validate explicit subscription upon subscription replacement"
        )
        self._step_update_oir_with_insufficient_explicit_sub()
        self._step_update_oir_with_sufficient_explicit_sub()
        self._step_delete_oir()
        self.end_test_case()

        # TODO move these 'basic' steps first in test scenario
        self.begin_test_case("Deletion requires correct OVN")
        self._step_create_oir()
        self._step_attempt_delete_missing_ovn()
        self._step_attempt_delete_incorrect_ovn()
        self._step_delete_oir()
        self.end_test_case()

        self.begin_test_case("Mutation requires correct OVN")
        self._step_create_oir()
        self._step_attempt_mutation_missing_ovn()
        self._step_attempt_mutation_incorrect_ovn()
        self._step_attempt_mutation_correct_ovn()
        self._step_delete_oir()
        self.end_test_case()

        self.end_test_scenario()

    def _step_create_subscription(self, params: SubscriptionParams) -> Subscription:
        self.begin_test_step("Create a subscription")
        with self.check("Create subscription query succeeds", self._pid) as check:
            mutated_sub = self._dss.upsert_subscription(**params)
            self.record_query(mutated_sub)
            if mutated_sub.status_code != 200:
                check.record_failed(
                    summary="Could not create subscription",
                    details=f"Failed to create subscription with error code {mutated_sub.status_code}: {mutated_sub.error_message}",
                    query_timestamps=[mutated_sub.timestamp],
                )
        self.end_test_step()
        return mutated_sub.subscription

    def _step_create_explicit_sub(self):
        self._sub_params = self._planning_area.get_new_subscription_params(
            subscription_id=self._sub_id,
            start_time=datetime.now() - timedelta(seconds=10),
            duration=timedelta(minutes=20),
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )
        self._current_sub = self._step_create_subscription(self._sub_params)

    def _create_oir(self, oir_params: PutOperationalIntentReferenceParameters):
        sub_id = oir_params.subscription_id if "subscription_id" in oir_params else None
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
                    subscription_id=sub_id,
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

    def _step_create_oir_insufficient_subscription(self):
        self.begin_test_step(
            "Provide subscription not covering extent of OIR being created"
        )

        oir_params = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.get_base_url(),
            time_start=datetime.now() - timedelta(seconds=10),
            time_end=self._sub_params.end_time
            + timedelta(seconds=1),  # OIR ends 1 sec after subscription
            subscription_id=self._sub_id,
        )

        with self.check(
            "Request to create OIR with too short subscription fails", self._pid
        ) as check:
            try:
                _, _, q = self._dss.put_op_intent(
                    extents=oir_params.extents,
                    key=oir_params.key,
                    state=oir_params.state,
                    base_url=oir_params.uss_base_url,
                    oi_id=self._oir_id,
                    subscription_id=oir_params.subscription_id,
                )
                self.record_query(q)
                # We don't expect to reach this point:
                check.record_failed(
                    summary="OIR creation with too short subscription was not expected to succeed",
                    details=f"Was expecting an HTTP 400 response because of an insufficient subscription, but got {q.status_code} instead",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code == 400:
                    pass
                else:
                    check.record_failed(
                        summary="OIR creation with too short subscription failed for unexpected reason",
                        details=f"Was expecting an HTTP 400 response because of an insufficient subscription, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )

        self.end_test_step()

    def _step_create_oir_sufficient_subscription(self):
        oir_params = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.get_base_url(),
            time_start=datetime.now() - timedelta(seconds=10),
            time_end=self._sub_params.end_time
            - timedelta(seconds=60),  # OIR ends at the same time as subscription
            subscription_id=self._sub_id,
        )

        self.begin_test_step("Create an OIR with correct explicit subscription")
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
                    subscription_id=oir_params.subscription_id,
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
        self._check_oir_has_correct_subscription(expected_sub_id=self._sub_id)
        self.end_test_step()

    def _step_update_oir_with_insufficient_explicit_sub(self):
        # Create another subscription that is a few seconds short of covering the OIR:
        oir_duration = (
            self._current_oir.time_end.value.datetime
            - self._current_oir.time_start.value.datetime
        )
        new_sub_params = self._planning_area.get_new_subscription_params(
            subscription_id=self._extra_sub_id,
            start_time=datetime.now() - timedelta(seconds=10),
            duration=oir_duration - timedelta(seconds=2),
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )

        self._current_extra_sub = self._step_create_subscription(new_sub_params)

        # Now attempt to mutate the OIR for it to use the invalid subscription:
        oir_update_params = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.get_base_url(),
            time_start=self._current_oir.time_start.value.datetime,
            time_end=self._current_oir.time_end.value.datetime,
            subscription_id=self._extra_sub_id,
        )

        self.begin_test_step(
            "Attempt to replace OIR's existing explicit subscription with an insufficient one"
        )
        with self.check(
            "Request to mutate OIR while providing a too short subscription fails",
            self._pid,
        ) as check:
            try:
                _, _, q = self._dss.put_op_intent(
                    extents=oir_update_params.extents,
                    key=oir_update_params.key,
                    state=oir_update_params.state,
                    base_url=oir_update_params.uss_base_url,
                    oi_id=self._oir_id,
                    subscription_id=oir_update_params.subscription_id,
                    ovn=self._current_oir.ovn,
                )
                self.record_query(q)
                # We don't expect to reach this point:
                check.record_failed(
                    summary="OIR mutation with too short subscription was not expected to succeed",
                    details=f"Was expecting an HTTP 400 response because of an insufficient subscription, but got {q.status_code} instead",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code == 400:
                    pass
                else:
                    check.record_failed(
                        summary="OIR mutation with too short subscription failed for unexpected reason",
                        details=f"Was expecting an HTTP 400 response because of an insufficient subscription, but got {qe.cause_status_code} instead. {qe.msg}",
                        query_timestamps=qe.query_timestamps,
                    )
        self._check_oir_has_correct_subscription(expected_sub_id=self._sub_id)
        self.end_test_step()

    def _step_update_oir_with_sufficient_explicit_sub(self):
        self.begin_test_step("Replace the OIR's explicit subscription")
        oir_update_params = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.get_base_url(),
            time_start=self._current_extra_sub.time_start.value.datetime,
            time_end=self._current_extra_sub.time_end.value.datetime,
            subscription_id=self._extra_sub_id,
        )
        with self.check(
            "Mutate operational intent reference query succeeds",
            self._pid,
        ) as check:
            try:
                mutated_oir, _, q = self._dss.put_op_intent(
                    extents=oir_update_params.extents,
                    key=oir_update_params.key,
                    state=oir_update_params.state,
                    base_url=oir_update_params.uss_base_url,
                    oi_id=self._oir_id,
                    subscription_id=oir_update_params.subscription_id,
                    ovn=self._current_oir.ovn,
                )
                self.record_query(q)
                self._current_oir = mutated_oir
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="OIR mutation with correct subscription failed",
                    details=f"Was expecting an HTTP 200 response for a mutation with valid parameters, but got {qe.cause_status_code} instead. {qe.msg}",
                    query_timestamps=qe.query_timestamps,
                )
        self._check_oir_has_correct_subscription(expected_sub_id=self._extra_sub_id)
        self.end_test_step()

    def _check_oir_has_correct_subscription(self, expected_sub_id: SubscriptionID):
        with self.check("Get operational intent reference by ID", self._pid) as check:
            try:
                oir, q = self._dss.get_op_intent_reference(self._oir_id)
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Could not get OIR",
                    details=f"Failed to get OIR with error code {qe.cause_status_code}: {qe.msg}",
                    query_timestamps=qe.query_timestamps,
                )

        with self.check("OIR is attached to expected subscription") as check:
            if oir.subscription_id != expected_sub_id:
                check.record_failed(
                    summary="OIR is not attached to the correct subscription",
                    details=f"Expected OIR to be attached to subscription {expected_sub_id}, but it is attached to {oir.subscription_id}",
                )

    def _step_attempt_delete_missing_ovn(self):

        self.begin_test_step("Attempt deletion with missing OVN")

        with self.check(
            "Request to delete OIR with empty OVN fails", self._pid
        ) as check:
            try:
                _, _, q = self._dss.delete_op_intent(self._oir_id, "")
                self.record_query(q)
                # We don't expect to reach this point:
                check.record_failed(
                    summary="OIR Deletion with empty OVN was not expected to succeed",
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
                        summary="OIR Deletion with empty OVN failed for unexpected reason",
                        details=f"Was expecting an HTTP 400, 404 or 409 response because of an empty OVN, but got {qe.cause_status_code} instead",
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
                # We don't expect to reach this point:
                check.record_failed(
                    summary="OIR Deletion with incorrect OVN was not expected to succeed",
                    details=f"Was expecting an HTTP 400, 404 or 409 response because of an incorrect OVN, but got {q.status_code} instead",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code in [400, 404, 409]:
                    # The spec explicitly requests a 409 response code for incorrect OVNs.
                    pass
                else:
                    check.record_failed(
                        summary="OIR Deletion with incorrect OVN failed for unexpected reason",
                        details=f"Was expecting an HTTP 400, 404 or 409 response because of an incorrect OVN, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )

        self.end_test_step()

    def _step_attempt_mutation_missing_ovn(self):

        self.begin_test_step("Attempt mutation with missing OVN")

        oir_params = self._test_params_for_current_time()
        with self.check(
            "Request to mutate OIR with empty OVN fails", self._pid
        ) as check:
            try:
                _, _, query = self._dss.put_op_intent(
                    extents=oir_params.extents,
                    key=oir_params.key,
                    state=oir_params.state,
                    base_url=oir_params.uss_base_url,
                    oi_id=self._oir_id,
                    ovn="",
                )
                self.record_query(query)
                # We don't expect to reach this point:
                check.record_failed(
                    summary="OIR Mutation with missing OVN was not expected to succeed",
                    details=f"Was expecting an HTTP 400, 404 or 409 response because of a missing OVN, but got {query.status_code} instead",
                    query_timestamps=[query.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code in [400, 404, 409]:
                    # An empty OVN can be seen as:
                    # an incorrect parameter (400), a reference to a non-existing entity (404) as well as a conflict (409)
                    pass
                else:
                    check.record_failed(
                        summary="OIR Mutation with missing OVN failed for unexpected reason",
                        details=f"Was expecting an HTTP 400, 404 or 409 response because of a missing OVN, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )
        self.end_test_step()

    def _step_attempt_mutation_incorrect_ovn(self):

        self.begin_test_step("Attempt mutation with incorrect OVN")

        oir_params = self._test_params_for_current_time()
        with self.check(
            "Request to mutate OIR with incorrect OVN fails", self._pid
        ) as check:
            try:
                _, _, query = self._dss.put_op_intent(
                    extents=oir_params.extents,
                    key=oir_params.key,
                    state=oir_params.state,
                    base_url=oir_params.uss_base_url,
                    oi_id=self._oir_id,
                    ovn="ThisIsAnIncorrectOVN",
                )
                self.record_query(query)
                # We don't expect to reach this point:
                check.record_failed(
                    summary="OIR Mutation with incorrect OVN was not expected to succeed",
                    details=f"Was expecting an HTTP 400, 404 or 409 response because of an incorrect OVN, but got {query.status_code} instead",
                    query_timestamps=[query.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code in [400, 404, 409]:
                    pass
                else:
                    check.record_failed(
                        summary="OIR Mutation with incorrect OVN failed for unexpected reason",
                        details=f"Was expecting an HTTP 400, 404 or 409 response because of an incorrect OVN, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )

        self.end_test_step()

    def _step_attempt_mutation_correct_ovn(self):

        self.begin_test_step("Attempt mutation with correct OVN")

        oir_params = self._test_params_for_current_time()
        with self.check(
            "Mutate operational intent reference query succeeds", self._pid
        ) as check:
            try:
                self._current_oir, _, query = self._dss.put_op_intent(
                    extents=oir_params.extents,
                    key=oir_params.key,
                    state=oir_params.state,
                    base_url=oir_params.uss_base_url + "?correct-ovn-mutation=true",
                    oi_id=self._oir_id,
                    ovn=self._current_oir.ovn,
                )
                self.record_query(query)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="OIR Mutation with correct OVN failed for unexpected reason",
                    details=f"Was expecting an 200 or 201 response because of an incorrect OVN, but got {qe.cause_status_code} instead",
                    query_timestamps=qe.query_timestamps,
                )

        self.end_test_step()

    def _step_create_oir(self):
        self.begin_test_step("Create OIR")
        self._setup_case(create_oir=True)
        self.end_test_step()

    def _setup_case(self, create_oir=False, create_explicit_sub=False):
        # Multiple runs of the scenario seem to rely on the same instance of it:
        # thus we need to reset the state of the scenario before running it.
        self._current_oir = None
        self._current_sub = None
        self._current_extra_sub = None

        if create_explicit_sub:
            self._step_create_explicit_sub()

        if create_oir:
            sub_id = self._sub_id if create_explicit_sub else None
            self._create_oir(
                oir_params=self._default_oir_params(subscription_id=sub_id)
            )

    def _delete_oir(self, oir_id: EntityID, ovn: str):
        with self.check(
            "Delete operational intent reference query succeeds", self._pid
        ) as check:
            try:
                _, _, query = self._dss.delete_op_intent(oir_id, ovn)
                self.record_query(query)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Could not delete operational intent reference",
                    details=f"Failed to delete operational intent reference with error code {qe.cause_status_code}: {qe.msg}",
                    query_timestamps=qe.query_timestamps,
                )

        self._current_oir = None

    def _step_delete_oir(self, is_cleanup: bool = True):
        if is_cleanup:
            self.begin_test_step("Cleanup OIR")
        else:
            self.begin_test_step("Delete OIR")
        self._delete_oir(self._oir_id, self._current_oir.ovn)
        self.end_test_step()

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

    def _ensure_clean_workspace(self):
        self.begin_test_step("Cleanup OIRs")
        self._clean_all_oirs()
        self.end_test_step()
        self.begin_test_step("Cleanup Subscriptions")
        self._clean_all_subs()
        self.end_test_step()

    def _clean_all_oirs(self):
        # Delete any active OIR we might own
        test_step_fragments.cleanup_active_oirs(
            self,
            self._dss,
            self._planning_area_volume4d.to_f3548v21(),
            self._expected_manager,
        )

        # Make sure the OIR IDs we are going to use are available
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)

    def _clean_all_subs(self):
        # Delete any active subscription we might own
        test_step_fragments.cleanup_active_subs(
            self,
            self._dss,
            self._planning_area_volume4d.to_f3548v21(),
        )

        # Make sure the subscription IDs we are going to use are available
        test_step_fragments.cleanup_sub(self, self._dss, self._sub_id)
        test_step_fragments.cleanup_sub(self, self._dss, self._extra_sub_id)

    def cleanup(self):
        self.begin_cleanup()
        self._clean_all_oirs()
        self._clean_all_subs()
        self.end_cleanup()

    def _test_params_for_current_time(self):
        return self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.get_base_url(),
            time_start=datetime.now() - timedelta(seconds=10),
            time_end=datetime.now() + timedelta(minutes=20),
            subscription_id=None,
        )

    def _default_oir_params(
        self, subscription_id: SubscriptionID
    ) -> PutOperationalIntentReferenceParameters:
        return self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.get_base_url(),
            time_start=datetime.now() - timedelta(seconds=10),
            time_end=datetime.now() + timedelta(minutes=20),
            subscription_id=subscription_id,
        )
