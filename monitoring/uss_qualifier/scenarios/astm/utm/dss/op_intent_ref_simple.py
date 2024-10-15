from datetime import datetime, timedelta
from typing import Optional

from uas_standards.astm.f3548.v21.api import (
    EntityID,
    OperationalIntentReference,
    OperationalIntentState,
    SubscriptionID,
    Subscription,
    PutOperationalIntentReferenceParameters,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.fetch.rid import subscription
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
from monitoring.uss_qualifier.resources.astm.f3548.v21.subscription_params import (
    SubscriptionParams,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext

# The official DSS implementation will set an OIR's subscription ID to 00000000-0000-4000-8000-000000000000
# when the OIR is not attached to any subscription, as the OpenAPI spec does not allow the value to be empty.
# Other implementations may use a different value. One way to check that an OIR is not attached to any subscription
# is to attempt to retrieve the subscription reportedly attached to it: if a 404 is returned then we may assume
# no subscription is attached.
# Note that this is only allowed for OIRs in the ACCEPTED state.
NULL_SUBSCRIPTION_ID = "00000000-0000-4000-8000-000000000000"


class OIRSimple(TestScenario):
    """
    A scenario that checks that Operational Intent references cannot be deleted with the incorrect OVN.

    TODO:
     - enrich with test case to mutate with incorrect OVN (planned via #760)
     - enrich with test case to delete with previous OVN (after mutation: add after #760)
    """

    OIR_TYPE = register_resource_type(396, "Operational Intent Reference")
    SUB_TYPE = register_resource_type(398, "Subscription")
    EXTRA_SUB_TYPE = register_resource_type(399, "Subscription")
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
        self._setup_case()
        self.end_test_case()

        self.begin_test_case(
            "OIR in ACCEPTED state can be created without subscription"
        )
        self._step_create_oir(
            oir_params=self._planning_area.get_new_operational_intent_ref_params(
                key=[],
                state=OperationalIntentState.Accepted,
                uss_base_url=self._planning_area.get_base_url(),
                time_start=datetime.now() - timedelta(seconds=10),
                time_end=datetime.now() + timedelta(minutes=20),
                subscription_id=None,
                implicit_sub_base_url=None,
            ),
        )
        self._step_oir_has_correct_subscription(expected_sub_id=None)
        self.end_test_case()

        self.begin_test_case(
            "Validate explicit subscription being attached to OIR without subscription"
        )
        self._step_update_oir_with_insufficient_explicit_sub(is_replacement=False)
        self._step_oir_has_correct_subscription(expected_sub_id=None)
        self._step_update_oir_with_sufficient_explicit_sub(is_replacement=False)
        self._step_oir_has_correct_subscription(expected_sub_id=self._extra_sub_id)
        self.end_test_case()

        self.begin_test_case("Validate explicit subscription on OIR creation")
        self._setup_case(create_explicit_sub=True)
        self._step_create_oir_insufficient_subscription()
        self._step_create_oir(
            oir_params=self._planning_area.get_new_operational_intent_ref_params(
                key=[],
                state=OperationalIntentState.Accepted,
                uss_base_url=self._planning_area.get_base_url(),
                time_start=datetime.now() - timedelta(seconds=10),
                time_end=self._sub_params.end_time,  # OIR ends at the same time as subscription
                subscription_id=self._sub_id,
            ),
        )
        self._step_oir_has_correct_subscription(expected_sub_id=self._sub_id)
        self.end_test_case()

        self.begin_test_case(
            "Validate explicit subscription upon subscription replacement"
        )
        self._step_update_oir_with_insufficient_explicit_sub(is_replacement=True)
        self._step_oir_has_correct_subscription(expected_sub_id=self._sub_id)
        self._step_update_oir_with_sufficient_explicit_sub(is_replacement=True)
        self._step_oir_has_correct_subscription(expected_sub_id=self._extra_sub_id)
        self.end_test_case()

        self.begin_test_case("Remove explicit subscription from OIR")
        self._step_remove_subscription_from_oir()
        self._step_oir_has_correct_subscription(expected_sub_id=None)
        self.end_test_case()

        self.begin_test_case("Deletion requires correct OVN")
        self._setup_case(create_oir=True)
        self._step_attempt_delete_missing_ovn()
        self._step_attempt_delete_incorrect_ovn()
        self.end_test_case()

        self.begin_test_case("Mutation requires correct OVN")
        self._step_attempt_mutation_missing_ovn()
        self._step_attempt_mutation_incorrect_ovn()
        self.end_test_case()

        self.end_test_scenario()

    def _step_create_subscription(self, params: SubscriptionParams) -> Subscription:
        self.begin_test_step("Create a subscription")
        with self.check("Create subscription query succeeds", self._pid) as check:
            try:
                mutated_sub = self._dss.upsert_subscription(**params)
                self.record_query(mutated_sub)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Could not create subscription",
                    details=f"Failed to create subscription with error code {qe.cause_status_code}: {qe.msg}",
                    query_timestamps=qe.query_timestamps,
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

    def _step_create_oir(self, oir_params: PutOperationalIntentReferenceParameters):
        self.begin_test_step("Create an operational intent reference")
        sub_id = oir_params.subscription_id if "subscription_id" in oir_params else None
        with self.check(
            "Create operational intent reference query succeeds",
            self._pid,
        ) as check:
            try:
                no_implicit_sub = (
                    "new_subscription" not in oir_params
                    or "uss_base_url" not in oir_params.new_subscription
                )
                new_oir, subs, query = self._dss.put_op_intent(
                    extents=oir_params.extents,
                    key=oir_params.key,
                    state=oir_params.state,
                    base_url=oir_params.uss_base_url,
                    oi_id=self._oir_id,
                    subscription_id=sub_id,
                    force_no_implicit_subscription=no_implicit_sub,
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
            "Request to create OIR with incorrect subscription fails", self._pid
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

    def _step_update_oir_with_insufficient_explicit_sub(self, is_replacement: bool):
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
        step_name = (
            "Attempt to replace OIR's existing explicit subscription with an insufficient one"
            if is_replacement
            else "Attempt to attach insufficient subscription to OIR"
        )
        self.begin_test_step(step_name)
        check_name = (
            "Request to mutate OIR while providing an incorrect subscription fails"
            if is_replacement
            else "Request to attach insufficient subscription to OIR fails"
        )
        with self.check(
            check_name,
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
                    summary="Request for OIR with too short subscription was not expected to succeed",
                    details=f"Was expecting an HTTP 400 response because of an insufficient subscription, but got {q.status_code} instead",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code == 400:
                    pass
                else:
                    check.record_failed(
                        summary="Request for OIR with too short subscription failed for unexpected reason",
                        details=f"Was expecting an HTTP 400 response because of an insufficient subscription, but got {qe.cause_status_code} instead. {qe.msg}",
                        query_timestamps=qe.query_timestamps,
                    )
        self.end_test_step()

    def _step_update_oir_with_sufficient_explicit_sub(self, is_replacement: bool):
        step_name = (
            "Replace the OIR's explicit subscription"
            if is_replacement
            else "Attach explicit subscription to OIR"
        )
        self.begin_test_step(step_name)
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
        self.end_test_step()

    def _step_remove_subscription_from_oir(self):
        self.begin_test_step("Remove explicit subscription from OIR")
        oir_update_params = self._planning_area.get_new_operational_intent_ref_params(
            key=[],
            state=OperationalIntentState.Accepted,
            uss_base_url=self._planning_area.get_base_url(),
            time_start=self._current_oir.time_start.value.datetime,
            time_end=self._current_oir.time_end.value.datetime,
            subscription_id=None,
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
                    subscription_id=None,
                    ovn=self._current_oir.ovn,
                    force_no_implicit_subscription=True,
                )
                self.record_query(q)
                self._current_oir = mutated_oir
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Removal of explicit subscription from OIR failed",
                    details=f"Was expecting an HTTP 200 response for a mutation with valid parameters, but got {qe.cause_status_code} instead. {qe.msg}",
                    query_timestamps=qe.query_timestamps,
                )
        self.end_test_step()

    def _step_oir_has_correct_subscription(
        self, expected_sub_id: Optional[SubscriptionID]
    ):
        step_check_name = (
            "OIR is attached to expected subscription"
            if expected_sub_id
            else "OIR is not attached to any subscription"
        )
        self.begin_test_step(step_check_name)
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

        sub_is_as_expected = False
        referenced_sub_was_found_when_non_expected = False
        if expected_sub_id is None:
            # The official DSS implementation will set the subscription ID to 00000000-0000-4000-8000-000000000000 when the OIR is not attached to any subscription.
            # Other implementations may use a different value, as the OpenAPI spec does not allow the value to be empty
            # We may at some point decide to tolerate accepting empty returned values here,
            # but in the meantime we simply attempt to obtain the subscription and check that it does not exist
            if oir.subscription_id == NULL_SUBSCRIPTION_ID:
                # Sub ID explicitly set to the value representing the null subscription: all good
                sub_is_as_expected = True
            elif oir.subscription_id is None:
                # Sub ID not set at all: not strictly compliant with the spec, but acceptable in this context
                sub_is_as_expected = True
            else:
                # If the subscription ID is defined and not set to the known 'null' value, we assume that the DSS used another
                # placeholder for the non-existing subscription, and we check that it does not exist.
                with self.check("Get referenced Subscription") as check:
                    sub = self._dss.get_subscription(oir.subscription_id)
                    self.record_query(sub)
                    if sub.status_code not in [200, 404]:
                        check.record_failed(
                            summary="Failed to try to obtain the subscription referenced by the OIR",
                            details=f"Failed in an unexpected way while querying subscription with ID {oir.subscription_id}: expected a 404 or 200, but got {sub.status_code}",
                            query_timestamps=[sub.request.timestamp],
                        )
                    if sub.status_code == 200:
                        referenced_sub_was_found_when_non_expected = True
        else:
            sub_is_as_expected = oir.subscription_id == expected_sub_id

        with self.check("OIR is attached to expected subscription", self._pid) as check:
            if referenced_sub_was_found_when_non_expected:
                check.record_failed(
                    summary="OIR is attached to a subscription although it should not be",
                    details=f"Expected OIR to not be attached to any subscription, but the referenced subscription {oir.subscription_id} does exist.",
                    query_timestamps=[sub.request.timestamp],
                )
            if not sub_is_as_expected:
                check.record_failed(
                    summary="OIR is not attached to the correct subscription",
                    details=f"Expected OIR to be attached to subscription {expected_sub_id}, but it is attached to {oir.subscription_id}",
                    query_timestamps=[q.request.timestamp],
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
                # We don't expect the reach this point:
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
                # We don't expect the reach this point:
                check.record_failed(
                    summary="OIR Mutation with incorrect OVN was not expected to succeed",
                    details=f"Was expecting an HTTP 409 response because of an incorrect OVN, but got {query.status_code} instead",
                    query_timestamps=[query.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code == 409:
                    pass
                else:
                    check.record_failed(
                        summary="OIR Mutation with incorrect OVN failed for unexpected reason",
                        details=f"Was expecting an HTTP 409 response because of an incorrect OVN, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )

        self.end_test_step()

    def _setup_case(self, create_oir=False, create_explicit_sub=False):
        # Multiple runs of the scenario seem to rely on the same instance of it:
        # thus we need to reset the state of the scenario before running it.
        self._current_oir = None
        self._current_sub = None
        self._current_extra_sub = None
        self.begin_test_step("Ensure clean workspace")
        self._ensure_clean_workspace_step()
        self.end_test_step()

        if create_oir:
            sub_id = self._sub_id if create_explicit_sub else None
            self._step_create_oir(
                oir_params=self._default_oir_params(subscription_id=sub_id)
            )

        if create_explicit_sub:
            self._step_create_explicit_sub()

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
