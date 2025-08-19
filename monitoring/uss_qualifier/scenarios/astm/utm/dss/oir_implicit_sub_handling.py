from datetime import datetime, timedelta

import arrow
from uas_standards.astm.f3548.v21.api import (
    EntityID,
    OperationalIntentReference,
    OperationalIntentState,
    PutOperationalIntentReferenceParameters,
    SubscriberToNotify,
    Subscription,
    SubscriptionID,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import Query, QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.testing import make_fake_url
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.oir import (
    check_oir_has_correct_subscription,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.oir.crud import (
    delete_oir_query,
    get_oir_query,
    update_oir_query,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.sub.crud import (
    sub_create_query,
    sub_delete_query,
    sub_get_query,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

OIR_A_TYPE = register_resource_type(391, "OIR for implicit sub handling")
OIR_B_TYPE = register_resource_type(392, "OIR for implicit sub handling")
OIR_C_TYPE = register_resource_type(393, "OIR for implicit sub handling")
SUB_TYPE = register_resource_type(394, "Subscription for implicit sub handling")

TIME_TOLERANCE_SEC = 1

# A scenario-specific base URL which will be used to easily identify the qualifier's subscriptions
DUMMY_BASE_URL = make_fake_url()


class OIRImplicitSubHandling(TestScenario):
    """
    A scenario that tests that a DSS properly handles the creation and mutation of implicit subscriptions
    """

    # Identifiers for the test OIRs
    _oir_a_id: str
    _oir_b_id: str
    _oir_c_id: str

    _sub_id: str

    _oir_a_ovn: str | None
    _oir_b_ovn: str | None

    # Reference times for the subscriptions and operational intents
    _time_0: datetime
    _time_1: datetime
    _time_2: datetime
    _time_3: datetime

    _manager: str

    # Keeps track of existing subscriptions in the planning area
    _initial_subscribers: list[SubscriberToNotify]
    _implicit_sub_1: Subscription | None
    _implicit_sub_2: Subscription | None
    _explicit_sub: Subscription | None

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        planning_area: PlanningAreaResource,
        utm_client_identity: ClientIdentityResource,
    ):
        """
        Args:
            dss: primary dss to test
            id_generator: will let us generate specific identifiers
            planning_area: An Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.
        """
        super().__init__()
        scopes = {
            Scope.StrategicCoordination: "create and delete operational intents with implicit subscriptions"
        }
        self._dss = dss.get_instance(scopes)
        self._pid = [self._dss.participant_id]
        self._planning_area = planning_area.specification

        self._oir_a_id = id_generator.id_factory.make_id(OIR_A_TYPE)
        self._oir_b_id = id_generator.id_factory.make_id(OIR_B_TYPE)
        self._oir_c_id = id_generator.id_factory.make_id(OIR_C_TYPE)
        self._sub_id = id_generator.id_factory.make_id(SUB_TYPE)

        self._manager = utm_client_identity.subject()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.begin_test_case("Setup")
        self._setup_scenario()
        self.end_test_case()

        self.begin_test_case(
            "Single OIR implicit subscription is removed upon OIR deletion"
        )
        self._case_1_implicit_sub_cleanup_on_oir_deletion()
        self.end_test_case()

        self.begin_test_case("Implicit subscriptions always properly cover their OIR")
        self._case_2_implicit_subs_cover_their_oir()
        self._clean_after_test_case()
        self.end_test_case()

        self.begin_test_case(
            "Implicit subscriptions are properly deleted when required by OIR mutation"
        )
        self._case_3_implicit_sub_deleted_after_oir_mutation()
        self._clean_after_test_case()
        self.end_test_case()

        self.begin_test_case("Implicit subscriptions are expanded as needed")
        self._case_4_implicit_sub_expansion()
        self._clean_after_test_case()
        self.end_test_case()

        self.begin_test_case(
            "Existing implicit subscription can replace an OIR's explicit subscription"
        )
        self._case_5_replace_explicit_sub_with_implicit()
        self._clean_after_test_case()
        self.end_test_case()

        self.begin_test_case(
            "Existing implicit subscription can be attached to OIR without subscription"
        )
        self._case_6_attach_implicit_sub_to_oir_without_subscription()
        self._clean_after_test_case()
        self.end_test_case()

        self.begin_test_case(
            "OIR without subscription can be mutated without a new subscription being attached"
        )

        self._case_7_mutate_oir_without_subscription()
        self._clean_after_test_case()
        self.end_test_case()

        self.begin_test_case(
            "Request new implicit subscription when mutating an OIR with existing explicit subscription"
        )
        self._case_8_mutate_oir_explicit_request_implicit()
        self._clean_after_test_case()
        self.end_test_case()

        self.begin_test_case(
            "Request new implicit subscription when mutating an OIR without subscription"
        )
        self._case_9_mutate_oir_nosub_request_implicit()
        self.end_test_case()
        self.end_test_scenario()

    def _case_1_implicit_sub_cleanup_on_oir_deletion(self):
        self.begin_test_step("Create an OIR with implicit subscription")
        self._case_1_step_create_oir_1()
        self.end_test_step()

        self.begin_test_step("Delete the OIR with implicit subscription")
        self._case_1_step_delete_single_oir()
        self.end_test_step()

    def _case_2_implicit_subs_cover_their_oir(self):
        self.begin_test_step("Create an OIR with implicit subscription")
        self._case_2_step_create_oir_1()
        self.end_test_step()

        self.begin_test_step("Create an overlapping OIR without any subscription")
        self._case_2_step_create_overlapping_oir_no_sub()
        self.end_test_step()

        self.begin_test_step(
            "Mutate OIR with implicit subscription to not overlap anymore"
        )
        self._case_2_step_mutate_oir_with_implicit_sub_specify_implicit_params()
        self.end_test_step()

        self.begin_test_step(
            "Create an OIR overlapping with the second OIR but not the first"
        )
        self._case_2_step_create_oir_2()
        self.end_test_step()

    def _case_3_implicit_sub_deleted_after_oir_mutation(self):
        self.begin_test_step("Create two OIRs with implicit subscription")
        self._case_3_create_oirs_with_implicit_sub()
        self.end_test_step()

        self.begin_test_step("Create a subscription")
        self._case_3_step_create_sub()
        self.end_test_step()

        self.begin_test_step(
            "Update OIR with implicit subscription to use explicit subscription"
        )
        self._case_3_update_oir_with_explicit_sub()
        self.end_test_step()

        self.begin_test_step(
            "Update OIR with implicit subscription to use no subscription"
        )
        self._case_3_update_oir_with_no_sub()
        self.end_test_step()

    def _case_4_implicit_sub_expansion(self):
        self.begin_test_step("Create an OIR with implicit subscription")
        self._case_4_create_oir()
        self.end_test_step()

        self.begin_test_step(
            "Expand the OIR while keeping the same implicit subscription"
        )
        self._case_4_expand_oir_same_implicit_sub()
        self.end_test_step()

    def _case_1_step_create_oir_1(self):
        oir, subs, impl_sub, _ = self._create_oir(
            self._oir_a_id, self._time_2, self._time_3, [], True
        )

        # We filter out the created implicit subscription from the list of subscribers to notify
        self._initial_subscribers = [
            sub for sub in subs if sub.uss_base_url != DUMMY_BASE_URL
        ]
        self._oir_a_ovn = oir.ovn
        self._implicit_sub_1 = impl_sub

    def _case_2_step_create_oir_1(self):
        oir, subs, impl_sub, _ = self._create_oir(
            self._oir_b_id, self._time_0, self._time_3, [], True
        )

        # TODO as a sanity check, confirm that subs don't contain a dangling implicit sub from the previous step
        self._oir_b_ovn = oir.ovn
        self._implicit_sub_2 = impl_sub

    def _case_2_step_create_overlapping_oir_no_sub(self):
        oir, subs, _, _ = self._create_oir(
            self._oir_c_id, self._time_2, self._time_3, [self._oir_b_ovn], False
        )

        with self.check(
            "New OIR creation response contains previous implicit subscription to notify",
            self._pid,
        ) as check:
            if self._implicit_sub_2.id not in to_sub_ids(subs):
                check.record_failed(
                    summary="Previous implicit subscription not found in subscribers to notify",
                    details=f"The subscription {self._implicit_sub_2.id} was not found among the subscribers of the new OIR: {subs}",
                )

        self._check_oir_has_correct_subscription(
            oir_id=self._oir_c_id, expected_sub_id=None
        )

        self._oir_c_ovn = oir.ovn

    def _case_2_step_mutate_oir_with_implicit_sub_specify_implicit_params(self):
        # Mutate the OIR with an implicit sub but don't mention the existing sub and
        # don't request an implicit sub.
        with self.check(
            "Mutate operational intent reference query succeeds", self._pid
        ) as check:
            try:
                oir, subs, q = self._dss.put_op_intent(
                    extents=[
                        self._planning_area.get_volume4d(
                            self._time_0, self._time_1
                        ).to_f3548v21()
                    ],
                    key=[],
                    state=OperationalIntentState.Accepted,
                    base_url=DUMMY_BASE_URL,
                    oi_id=self._oir_b_id,
                    ovn=self._oir_b_ovn,
                    # We want to observe the behavior if the request to the DSS
                    # contains the implicit sub params (default when subscription_id is None)
                    subscription_id=None,
                )
                self.record_query(q)
                self._oir_b_ovn = oir.ovn
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="OIR Mutation failed",
                    details=str(e),
                    query_timestamps=e.query_timestamps,
                )

        with self.check("The implicit subscription can be queried", self._pid) as check:
            sub = self._dss.get_subscription(oir.subscription_id)
            self.record_query(sub)
            if not sub.success:
                check.record_failed(
                    summary="Subscription query failed",
                    details=f"Failed to query subscription {oir.subscription_id} with code {sub.response.status_code}. Message: {sub.error_message}",
                    query_timestamps=sub.query_timestamps,
                )

        # Also check that the subscription parameters match the temporality of the OIR:
        with self.check(
            "Implicit subscription has correct temporal parameters", self._pid
        ) as check:
            if (
                abs(
                    sub.subscription.time_start.value.datetime - self._time_0
                ).total_seconds()
                > TIME_TOLERANCE_SEC
            ):
                check.record_failed(
                    summary="Subscription time_start does not match OIR",
                    details=f"Subscription time_start is {sub.subscription.time_start.value.datetime}, expected {self._time_0}",
                    query_timestamps=[sub.request.timestamp],
                )
            if (
                abs(
                    sub.subscription.time_end.value.datetime - self._time_1
                ).total_seconds()
                > TIME_TOLERANCE_SEC
            ):
                check.record_failed(
                    summary="Subscription time_end does not match OIR",
                    details=f"Subscription time_end is {sub.subscription.time_end.value.datetime}, expected {self._time_0}",
                    query_timestamps=[sub.request.timestamp],
                )

        if sub.subscription.id != self._implicit_sub_2.id:
            # Mutation caused the creation of a new implicit subscription:
            # Need to confirm that the old implicit subscription was removed

            with self.check(
                "Non-mutated implicit subscription is deleted", self._pid
            ) as check:
                sub_exp_fail = self._dss.get_subscription(self._implicit_sub_2.id)
                self.record_query(sub_exp_fail)
                if sub_exp_fail.status_code != 404:
                    check.record_failed(
                        summary="Previous implicit subscription still exists",
                        details=f"Subscription {self._implicit_sub_2.id} was not deleted after the OIR it was attached to was mutated and attached to a new implicit subscription.",
                        query_timestamps=[sub_exp_fail.request.timestamp],
                    )

    def _case_2_step_create_oir_2(self):
        oir, subs, _, q = self._create_oir(
            self._oir_a_id, self._time_2, self._time_3, [self._oir_c_ovn], False
        )

        self._oir_a_ovn = oir.ovn

        with self.check(
            "Within a temporal frame not overlapping a newly created implicit subscription, subscriptions should be the same as at the start of the test case",
            self._pid,
        ) as check:
            if to_sub_ids(subs) != to_sub_ids(self._initial_subscribers):
                check.record_failed(
                    summary="Subscriptions not left as before",
                    details=f"Subscription outside of remaining implicit subscriptions {subs} are not the same as the initial subscriptions: {self._initial_subscribers}",
                    query_timestamps=[q.request.timestamp],
                )

        self._check_oir_has_correct_subscription(
            oir_id=self._oir_a_id, expected_sub_id=None
        )

    def _create_oir(
        self,
        oir_id,
        time_start,
        time_end,
        relevant_ovns,
        with_implicit_sub,
        subscription_id=None,
    ) -> tuple[
        OperationalIntentReference,
        list[SubscriberToNotify],
        Subscription | None,
        Query,
    ]:
        """

        Args:
            oir_id: Identifier for the OIR
            time_start: when the OIR starts
            time_end: when the OIR ends
            with_implicit_sub: if true, an implicit subscription will be created.

        Returns:
            A triple of:
             - the created OIR
             - a list of subscribers that need to be notified
             - the implicit subscription that was created, if it was requested

        """

        with self.check(
            "Create operational intent reference query succeeds", self._pid
        ) as check:
            try:
                oir, subs, oir_q = self._dss.put_op_intent(
                    extents=[
                        self._planning_area.get_volume4d(
                            time_start, time_end
                        ).to_f3548v21()
                    ],
                    key=relevant_ovns,
                    state=OperationalIntentState.Accepted,
                    base_url=DUMMY_BASE_URL,
                    oi_id=oir_id,
                    ovn=None,
                    subscription_id=subscription_id,
                    force_no_implicit_subscription=not with_implicit_sub,
                )
                self.record_query(oir_q)
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="OIR Creation failed",
                    details=str(e),
                    query_timestamps=e.query_timestamps,
                )

        implicit_sub = None
        if with_implicit_sub:
            with self.check(
                "An implicit subscription was created and can be queried", self._pid
            ) as check:
                sub = self._dss.get_subscription(oir.subscription_id)
                self.record_query(sub)
                if not sub.success:
                    check.record_failed(
                        summary="Subscription query failed",
                        details=f"Failed to query subscription {oir.subscription_id} with code {sub.response.status_code}. Message: {sub.error_message}",
                        query_timestamps=sub.query_timestamps,
                    )

            # Also check that the subscription parameters match the temporality of the OIR:
            # If we have issues because of dangling subscriptions this can help us identify the issue
            with self.check(
                "Implicit subscription has correct temporal parameters", self._pid
            ) as check:
                if (
                    abs(
                        sub.subscription.time_start.value.datetime - time_start
                    ).total_seconds()
                    > TIME_TOLERANCE_SEC
                ):
                    check.record_failed(
                        summary="Subscription time_start does not match OIR",
                        details=f"Subscription time_start is {sub.subscription.time_start.value.datetime}, expected {time_start}",
                        query_timestamps=[sub.request.timestamp],
                    )
                if (
                    abs(
                        sub.subscription.time_end.value.datetime - time_end
                    ).total_seconds()
                    > TIME_TOLERANCE_SEC
                ):
                    check.record_failed(
                        summary="Subscription time_end does not match OIR",
                        details=f"Subscription time_end is {sub.subscription.time_end.value.datetime}, expected {time_end}",
                        query_timestamps=[sub.request.timestamp],
                    )
            implicit_sub = sub.subscription
        elif subscription_id is None:
            with self.check(
                "OIR is not attached to a subscription", self._pid
            ) as check:
                # The official DSS implementation will set the subscription ID to 00000000-0000-4000-8000-000000000000
                # Other implementations may use a different value, as the OpenAPI spec does not allow the value to be empty
                # We may at some point decide to tolerate accepting empty returned values here,
                # but in the meantime we simply attempt to obtain the subscription and check that it does not exist
                sub = self._dss.get_subscription(oir.subscription_id)
                self.record_query(sub)
                if sub.status_code != 404:
                    check.record_failed(
                        summary="Implicit subscription was created",
                        details=f"Subscription {oir.subscription_id} was created when it was not expected to be.",
                        query_timestamps=[sub.request.timestamp],
                    )

            implicit_sub = None

        return oir, subs, implicit_sub, oir_q

    def _case_1_step_delete_single_oir(self):
        with self.check(
            "Delete operational intent reference query succeeds", self._pid
        ) as check:
            try:
                deleted_oir, subs, q = self._dss.delete_op_intent(
                    self._oir_a_id, self._oir_a_ovn
                )
                self.record_query(q)
                self._oir_a_ovn = None
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="OIR Deletion failed",
                    details=str(e),
                    query_timestamps=e.query_timestamps,
                )

        with self.check("The implicit subscription was removed", self._pid) as check:
            non_existing_sub = self._dss.get_subscription(self._implicit_sub_1.id)
            self.record_query(non_existing_sub)
            # non_existing_sub.success will return true on a 404
            if not non_existing_sub.errors and non_existing_sub.status_code != 404:
                check.record_failed(
                    summary="Subscription still exists",
                    details=f"Subscription {self._implicit_sub_1.id} is still returned, while it was expected to not be found.",
                    query_timestamps=[non_existing_sub.request.timestamp],
                )
            elif non_existing_sub.status_code != 404:
                check.record_failed(
                    summary=f"Unexpected error code: {non_existing_sub.response.status_code}",
                    details=f"Querying subscription {self._implicit_sub_1.subscription_id}, which is not expected to exist, should result in an HTTP 404 error. Got {non_existing_sub.response.status_code} instead.",
                    query_timestamps=[non_existing_sub.request.timestamp],
                )

        self._implicit_sub_1 = None

        with self.check(
            "After removal of the only created OIR, subscriptions should be as before its creation",
            self._pid,
        ) as check:
            no_self_subs = [sub for sub in subs if sub.uss_base_url != DUMMY_BASE_URL]
            if to_sub_ids(no_self_subs) != to_sub_ids(self._initial_subscribers):
                check.record_failed(
                    summary="Subscriptions not left as before",
                    details=f"Subscriptions after the OIR with implicit subscription was deleted: {subs} are not the same as the initial subscriptions: {self._initial_subscribers}",
                    query_timestamps=[non_existing_sub.request.timestamp],
                )

    def _case_3_create_oirs_with_implicit_sub(self):
        oir_a, _, impl_sub_1, _ = self._create_oir(
            self._oir_a_id, self._time_0, self._time_1, [], True
        )

        self._oir_a_ovn = oir_a.ovn
        self._implicit_sub_1 = impl_sub_1

        oir_b, _, impl_sub_2, _ = self._create_oir(
            self._oir_b_id, self._time_2, self._time_3, [], True
        )

        self._oir_b_ovn = oir_b.ovn
        self._implicit_sub_2 = impl_sub_2

    def _case_3_step_create_sub(self):
        self._explicit_sub, _, _ = sub_create_query(
            self,
            self._dss,
            self._planning_area.get_new_subscription_params(
                self._sub_id,
                self._time_0,
                self._time_1 - self._time_0,
                notify_for_op_intents=True,
                notify_for_constraints=False,
            ),
        )

    def _case_3_update_oir_with_explicit_sub(self):
        # Set the OIR's subscription to the explicit subscription we created
        with self.check(
            "Mutate operational intent reference query succeeds", self._pid
        ) as check:
            try:
                oir, subs, q = self._dss.put_op_intent(
                    extents=[
                        self._planning_area.get_volume4d(
                            self._time_0, self._time_1
                        ).to_f3548v21()
                    ],
                    key=[],
                    state=OperationalIntentState.Accepted,
                    base_url=DUMMY_BASE_URL,
                    oi_id=self._oir_a_id,
                    ovn=self._oir_a_ovn,
                    # We want to observe the behavior if the request to the DSS
                    # contains the implicit sub params (default when subscription_id is None)
                    subscription_id=self._explicit_sub.id,
                )
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="OIR Creation failed",
                    details=str(e),
                    query_timestamps=e.query_timestamps,
                )

        self._oir_a_ovn = oir.ovn

        # Now check that the previously attached implicit subscription is not present anymore
        with self.check(
            "Previously attached implicit subscription was deleted", self._pid
        ) as check:
            sub_exp_fail = self._dss.get_subscription(self._implicit_sub_1.id)
            self.record_query(sub_exp_fail)
            if sub_exp_fail.status_code != 404:
                check.record_failed(
                    summary="Previous implicit subscription still exists",
                    details=f"Subscription {self._implicit_sub_1.id} was not deleted after the OIR it was attached to was mutated and attached to an explicitly created subscription.",
                    query_timestamps=[sub_exp_fail.request.timestamp],
                )

    def _case_3_update_oir_with_no_sub(self):
        # Mutate the OIR so it has no more subscription
        with self.check(
            "Mutate operational intent reference query succeeds", self._pid
        ) as check:
            try:
                oir, subs, q = self._dss.put_op_intent(
                    extents=[
                        self._planning_area.get_volume4d(
                            self._time_2, self._time_3
                        ).to_f3548v21()
                    ],
                    key=[],
                    state=OperationalIntentState.Accepted,
                    base_url=DUMMY_BASE_URL,
                    oi_id=self._oir_b_id,
                    ovn=self._oir_b_ovn,
                    force_no_implicit_subscription=True,
                )
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="OIR Creation failed",
                    details=str(e),
                    query_timestamps=e.query_timestamps,
                )

        self._oir_b_ovn = oir.ovn

        # Now check that the previously attached implicit subscription is not present anymore
        with self.check(
            "Previously attached implicit subscription was deleted", self._pid
        ) as check:
            sub_exp_fail = self._dss.get_subscription(self._implicit_sub_2.id)
            self.record_query(sub_exp_fail)
            if sub_exp_fail.status_code != 404:
                check.record_failed(
                    summary="Previous implicit subscription still exists",
                    details=f"Subscription {self._implicit_sub_2.id} was not deleted after the OIR it was attached to was mutated to not have a subscription anymore.",
                    query_timestamps=[sub_exp_fail.request.timestamp],
                )

    def _case_4_create_oir(self):
        oir_a, _, impl_sub_1, _ = self._create_oir(
            self._oir_a_id, self._time_0, self._time_1, [], with_implicit_sub=True
        )

        self._oir_a_ovn = oir_a.ovn
        self._implicit_sub_1 = impl_sub_1

    def _case_4_expand_oir_same_implicit_sub(self):
        # Mutate the OIR so it is slightly longer and
        # specify the implicit sub previously created for that OIR
        with self.check(
            "Mutate operational intent reference query succeeds", self._pid
        ) as check:
            try:
                oir, subs, q = self._dss.put_op_intent(
                    extents=[
                        self._planning_area.get_volume4d(
                            self._time_0, self._time_2
                        ).to_f3548v21()
                    ],
                    key=[],
                    state=OperationalIntentState.Accepted,
                    base_url=DUMMY_BASE_URL,
                    oi_id=self._oir_a_id,
                    ovn=self._oir_a_ovn,
                    subscription_id=self._implicit_sub_1.id,
                )
                self.record_query(q)
                self._oir_a_ovn = oir.ovn
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="OIR Creation failed",
                    details=str(e),
                    query_timestamps=e.query_timestamps,
                )

        with self.check("The implicit subscription can be queried", self._pid) as check:
            sub = self._dss.get_subscription(self._implicit_sub_1.id)
            self.record_query(sub)
            if sub.status_code != 200:
                check.record_failed(
                    summary="Subscription query failed",
                    details=f"Failed to query previously created implicit subscription {oir.subscription_id} with code {sub.response.status_code}. Message: {sub.error_message}",
                    query_timestamps=sub.query_timestamps,
                )

        with self.check(
            "Implicit subscription has wide enough temporal parameters", self._pid
        ) as check:
            if (
                abs(
                    sub.subscription.time_start.value.datetime - self._time_0
                ).total_seconds()
                > TIME_TOLERANCE_SEC
            ):
                check.record_failed(
                    summary="Subscription time_start does not match OIR",
                    details=f"Subscription time_start is {sub.subscription.time_start.value.datetime}, expected {self._time_0}",
                    query_timestamps=[sub.request.timestamp],
                )
            if (
                abs(
                    sub.subscription.time_end.value.datetime - self._time_2
                ).total_seconds()
                > TIME_TOLERANCE_SEC
            ):
                check.record_failed(
                    summary="Subscription time_end does not match OIR",
                    details=f"Subscription time_end is {sub.subscription.time_end.value.datetime}, expected {self._time_0}",
                    query_timestamps=[sub.request.timestamp],
                )

    def _case_5_replace_explicit_sub_with_implicit(self):
        self.begin_test_step("Create an explicit subscription")
        sub_params = self._planning_area.get_new_subscription_params(
            subscription_id=self._sub_id,
            start_time=datetime.now() - timedelta(seconds=10),
            duration=timedelta(minutes=20),
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )
        self._explicit_sub, _, _ = sub_create_query(self, self._dss, sub_params)
        self.end_test_step()

        self.begin_test_step("Create first OIR with an explicit subscription")
        oir_explicit, _, _, _ = self._create_oir(
            oir_id=self._oir_a_id,
            time_start=self._explicit_sub.time_start.value.datetime,
            time_end=self._explicit_sub.time_end.value.datetime,
            relevant_ovns=[],
            with_implicit_sub=False,
            subscription_id=self._explicit_sub.id,
        )
        self._oir_a_ovn = oir_explicit.ovn
        self.end_test_step()

        self.begin_test_step("Create second OIR with an implicit subscription")
        oir_implicit, _, sub_implicit, _ = self._create_oir(
            oir_id=self._oir_b_id,
            time_start=self._explicit_sub.time_start.value.datetime,
            time_end=self._explicit_sub.time_end.value.datetime,
            relevant_ovns=[oir_explicit.ovn],
            with_implicit_sub=True,
        )
        self._oir_b_ovn = oir_implicit.ovn
        self._implicit_sub_1 = sub_implicit
        self.end_test_step()

        self.begin_test_step(
            "Replace first OIR's explicit subscription with implicit subscription"
        )
        with self.check(
            "Mutate operational intent reference query succeeds", self._pid
        ) as check:
            try:
                oir, subs, q = self._dss.put_op_intent(
                    extents=[
                        self._planning_area.get_volume4d(
                            self._explicit_sub.time_start.value.datetime,
                            self._explicit_sub.time_end.value.datetime,
                        ).to_f3548v21()
                    ],
                    key=[oir_implicit.ovn],
                    state=OperationalIntentState.Accepted,
                    base_url=DUMMY_BASE_URL,
                    oi_id=self._oir_a_id,
                    ovn=self._oir_a_ovn,
                    # We want to observe the behavior if the request to the DSS
                    # contains the implicit sub params (default when subscription_id is None)
                    subscription_id=sub_implicit.id,
                )
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="OIR Creation failed",
                    details=str(e),
                    query_timestamps=e.query_timestamps,
                )

        self._oir_a_ovn = oir.ovn

        with self.check(
            "OIR is attached to expected subscription",
            self._pid,
        ) as check:
            if sub_implicit.id != oir.subscription_id:
                check.record_failed(
                    summary="Implicit subscription not attached to OIR",
                    details=f"The subscription {sub_implicit.id} was attached to the OIR, but it reports being attached to subscription {oir.subscription_id} instead.",
                )

        self._check_oir_has_correct_subscription(
            oir_id=self._oir_a_id, expected_sub_id=sub_implicit.id
        )

        self.end_test_step()

    def _case_6_attach_implicit_sub_to_oir_without_subscription(self):
        self.begin_test_step("Create OIR with no subscription")
        oir_no_sub, _, _, _ = self._create_oir(
            oir_id=self._oir_a_id,
            time_start=self._time_2,
            time_end=self._time_3,
            relevant_ovns=[],
            with_implicit_sub=False,
        )
        self._oir_a_ovn = oir_no_sub.ovn
        check_oir_has_correct_subscription(
            self,
            self._dss,
            self._oir_a_id,
            expected_sub_id=None,
        )
        self.end_test_step()

        self.begin_test_step("Create second OIR with an implicit subscription")
        oir_implicit, _, sub_implicit, _ = self._create_oir(
            oir_id=self._oir_b_id,
            time_start=oir_no_sub.time_start.value.datetime,
            time_end=oir_no_sub.time_end.value.datetime,
            relevant_ovns=[oir_no_sub.ovn],
            with_implicit_sub=True,
        )
        self._oir_b_ovn = oir_implicit.ovn
        self._implicit_sub_1 = sub_implicit
        self.end_test_step()

        self.begin_test_step("Attach OIR without subscription to implicit subscription")
        with self.check(
            "Mutate operational intent reference query succeeds", self._pid
        ) as check:
            try:
                oir_updated, subs, q = self._dss.put_op_intent(
                    extents=[
                        self._planning_area.get_volume4d(
                            oir_no_sub.time_start.value.datetime,
                            oir_no_sub.time_end.value.datetime,
                        ).to_f3548v21()
                    ],
                    key=[oir_implicit.ovn],
                    state=OperationalIntentState.Accepted,
                    base_url=DUMMY_BASE_URL,
                    oi_id=self._oir_a_id,
                    ovn=self._oir_a_ovn,
                    subscription_id=sub_implicit.id,
                )
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="OIR Creation failed",
                    details=str(e),
                    query_timestamps=e.query_timestamps,
                )

        self._oir_a_ovn = oir_updated.ovn

        self.end_test_step()

        self.begin_test_step("Confirm OIR is now attached to implicit subscription")

        # First, sanity check of the value reported by the DSS at the previous step
        with self.check(
            "OIR is attached to expected subscription",
            self._pid,
        ) as check:
            if sub_implicit.id != oir_updated.subscription_id:
                check.record_failed(
                    summary="Implicit subscription not attached to OIR",
                    details=f"The subscription {sub_implicit.id} was attached to the OIR, but it reports being attached to subscription {oir_no_sub.subscription_id} instead.",
                )

        # Then, do an actual query of the OIR
        with self.check("Get operational intent reference by ID", self._pid) as check:
            try:
                oir_queried, _ = self._dss.get_op_intent_reference(self._oir_a_id)

            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="OIR query failed",
                    details=str(e),
                    query_timestamps=e.query_timestamps,
                )

        with self.check(
            "OIR is attached to expected subscription",
            self._oir_a_id,
        ) as check:
            if sub_implicit.id != oir_queried.subscription_id:
                check.record_failed(
                    summary="Implicit subscription not attached to OIR",
                    details=f"The subscription {sub_implicit.id} was attached to the OIR, but it reports being attached to subscription {oir_queried.subscription_id} instead.",
                )

        self.end_test_step()

    def _case_7_mutate_oir_without_subscription(self):
        self.begin_test_step("Create OIR with no subscription")
        oir_no_sub, _, _, _ = self._create_oir(
            oir_id=self._oir_a_id,
            time_start=self._time_2,
            time_end=self._time_3,
            relevant_ovns=[],
            with_implicit_sub=False,
        )
        self._oir_a_ovn = oir_no_sub.ovn
        check_oir_has_correct_subscription(
            self,
            self._dss,
            self._oir_a_id,
            expected_sub_id=None,
        )
        self.end_test_step()

        self.begin_test_step("Mutate OIR without adding a subscription")
        with self.check(
            "Mutate operational intent reference query succeeds", self._pid
        ) as check:
            try:
                oir_mutated_no_sub, _, q = self._dss.put_op_intent(
                    extents=[
                        self._planning_area.get_volume4d(
                            self._time_0, self._time_1
                        ).to_f3548v21()
                    ],
                    key=[],
                    state=OperationalIntentState.Accepted,
                    base_url=DUMMY_BASE_URL,
                    oi_id=self._oir_a_id,
                    ovn=self._oir_a_ovn,
                    subscription_id=None,
                    force_no_implicit_subscription=True,
                )
                self.record_query(q)
                self._oir_a_ovn = oir_mutated_no_sub.ovn
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="OIR Mutation failed",
                    details=str(e),
                    query_timestamps=e.query_timestamps,
                )
        check_oir_has_correct_subscription(
            self,
            self._dss,
            self._oir_a_id,
            expected_sub_id=None,
        )
        self.end_test_step()

    def _case_8_mutate_oir_explicit_request_implicit(self):
        self.begin_test_step("Create an explicit subscription")
        sub_params = self._planning_area.get_new_subscription_params(
            subscription_id=self._sub_id,
            start_time=self._time_2,
            duration=self._time_3 - self._time_2,
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )
        self._explicit_sub, _, _ = sub_create_query(self, self._dss, sub_params)
        self.end_test_step()

        self.begin_test_step("Create OIR with explicit subscription")
        oir_explicit_sub, _, _, _ = self._create_oir(
            oir_id=self._oir_a_id,
            time_start=self._time_2,
            time_end=self._time_3,
            relevant_ovns=[],
            subscription_id=self._sub_id,
            with_implicit_sub=False,
        )
        self._oir_a_ovn = oir_explicit_sub.ovn
        check_oir_has_correct_subscription(
            self,
            self._dss,
            self._oir_a_id,
            expected_sub_id=self._sub_id,
        )
        self.end_test_step()

        self.begin_test_step("Mutate OIR to request new implicit subscription")
        oir_mutated_to_implicit_sub, _, q = update_oir_query(
            scenario=self,
            dss=self._dss,
            oir_id=self._oir_a_id,
            ovn=self._oir_a_ovn,
            oir_params=PutOperationalIntentReferenceParameters(
                extents=[
                    self._planning_area.get_volume4d(
                        self._time_2, self._time_3
                    ).to_f3548v21()
                ],
                key=[],
                # Update to a state that requires a subscription
                state=OperationalIntentState.Activated,
                uss_base_url=DUMMY_BASE_URL,
                subscription_id=None,
            ),
        )
        self._oir_a_ovn = oir_mutated_to_implicit_sub.ovn
        self.end_test_step()

        self.begin_test_step(
            "Validate that the OIR is now attached to an implicit subscription"
        )

        def check_sub_changed(oir, mutate_q):
            with self.check(
                "OIR is attached to a new subscription", self._pid
            ) as check:
                if oir.subscription_id is None:
                    check.record_failed(
                        summary="OIR not attached to any subscription",
                        details="OIR is not attached to any subscription, when a request for an implicit subscription was made.",
                        query_timestamps=[mutate_q.timestamp],
                    )
                if oir.subscription_id == self._explicit_sub.id:
                    check.record_failed(
                        summary="OIR is still attached to the explicit subscription",
                        details=f"OIR is still attached to the explicit subscription {self._explicit_sub.id}, when a request for an implicit subscription was made.",
                        query_timestamps=[mutate_q.timestamp],
                    )

        # First check the OIR as it was returned by the mutation endpoint
        check_sub_changed(oir_mutated_to_implicit_sub, q)

        # Then, do an actual query of the OIR
        oir_queried, q = get_oir_query(self, self._dss, self._oir_a_id)

        check_sub_changed(oir_queried, q)

        # Now fetch the subscription and check it is implicit
        fetched_sub, _ = sub_get_query(self, self._dss, oir_queried.subscription_id)

        with self.check(
            "OIR is now attached to an implicit subscription", self._pid
        ) as check:
            if not fetched_sub.implicit_subscription:
                check.record_failed(
                    summary="OIR is not attached to an implicit subscription",
                    details=f"Subscription {self._sub_id} referenced by OIR {self._oir_a_id} is not an implicit subscription.",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

        self.end_test_step()

    def _case_9_mutate_oir_nosub_request_implicit(self):
        self.begin_test_step("Create OIR with no subscription")
        oir_no_sub, _, _, _ = self._create_oir(
            oir_id=self._oir_a_id,
            time_start=self._time_2,
            time_end=self._time_3,
            relevant_ovns=[],
            with_implicit_sub=False,
        )
        self._oir_a_ovn = oir_no_sub.ovn
        check_oir_has_correct_subscription(
            self,
            self._dss,
            self._oir_a_id,
            expected_sub_id=None,
        )
        self.end_test_step()
        self.begin_test_step("Mutate OIR to request new implicit subscription")
        oir_mutated_to_implicit_sub, _, _ = update_oir_query(
            scenario=self,
            dss=self._dss,
            oir_id=self._oir_a_id,
            ovn=self._oir_a_ovn,
            oir_params=PutOperationalIntentReferenceParameters(
                extents=[
                    self._planning_area.get_volume4d(
                        self._time_2, self._time_3
                    ).to_f3548v21()
                ],
                key=[],
                # Update to a state that requires a subscription
                state=OperationalIntentState.Activated,
                uss_base_url=DUMMY_BASE_URL,
                subscription_id=None,
            ),
        )
        self._oir_a_ovn = oir_mutated_to_implicit_sub.ovn
        self.end_test_step()
        self.begin_test_step(
            "Validate that the OIR is now attached to an implicit subscription"
        )

        def check_sub_not_none(oir):
            with self.check(
                "OIR is attached to a new subscription", self._pid
            ) as check:
                if oir.subscription_id is None:
                    check.record_failed(
                        summary="OIR not attached to any subscription",
                        details="OIR is not attached to any subscription, when a request for an implicit subscription was made.",
                    )

        # First check the OIR as it was returned by the mutation endpoint
        check_sub_not_none(oir_mutated_to_implicit_sub)

        # Then, do an actual query of the OIR
        oir_queried, _ = get_oir_query(self, self._dss, self._oir_a_id)

        check_sub_not_none(oir_queried)

        # Now fetch the subscription and check it is implicit
        fetched_sub, _ = sub_get_query(self, self._dss, oir_queried.subscription_id)

        with self.check(
            "OIR is now attached to an implicit subscription", self._pid
        ) as check:
            if not fetched_sub.implicit_subscription:
                check.record_failed(
                    summary="OIR is not attached to an implicit subscription",
                    details=f"Subscription {self._sub_id} referenced by OIR {self._oir_a_id} is not an implicit subscription.",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

        self.end_test_step()

    def _check_oir_has_correct_subscription(
        self, oir_id: EntityID, expected_sub_id: SubscriptionID | None
    ):
        check_oir_has_correct_subscription(
            self,
            self._dss,
            oir_id,
            expected_sub_id,
        )

    def _setup_scenario(self):
        # T0 corresponds to 'now'
        self._time_0 = arrow.utcnow().datetime

        # T1, T2 and T3 are chronologically ordered and relatively far from T0
        self._time_1 = self._time_0 + timedelta(hours=20)
        self._time_2 = self._time_1 + timedelta(hours=1)
        self._time_3 = self._time_2 + timedelta(hours=1)

        self._ensure_clean_workspace_step()

        self._oir_a_ovn = None
        self._oir_b_ovn = None
        self._oir_c_ovn = None

        self._initial_subscribers = []
        self._implicit_sub_1 = None
        self._implicit_sub_2 = None
        self._explicit_sub = None

    def _ensure_clean_workspace_step(self):
        self.begin_test_step("Ensure clean workspace")
        self._clean_workspace()
        self.end_test_step()

    def _clean_workspace(self):
        extents = Volume4D(volume=self._planning_area.volume)
        test_step_fragments.cleanup_active_oirs(
            self,
            self._dss,
            extents,
            self._manager,
        )
        for oir_id in [self._oir_a_id, self._oir_b_id, self._oir_c_id]:
            test_step_fragments.cleanup_op_intent(self, self._dss, oir_id)
        test_step_fragments.cleanup_active_subs(
            self,
            self._dss,
            extents,
        )
        test_step_fragments.cleanup_sub(self, self._dss, self._sub_id)

    def _clean_after_test_case(self):
        self.begin_test_step("Cleanup After Test Case")

        if self._oir_a_ovn:
            delete_oir_query(
                scenario=self, dss=self._dss, oir_id=self._oir_a_id, ovn=self._oir_a_ovn
            )
            self._oir_a_ovn = None

        if self._oir_b_ovn:
            delete_oir_query(
                scenario=self, dss=self._dss, oir_id=self._oir_b_id, ovn=self._oir_b_ovn
            )
            self._oir_b_ovn = None

        if self._oir_c_ovn:
            delete_oir_query(
                scenario=self, dss=self._dss, oir_id=self._oir_c_id, ovn=self._oir_c_ovn
            )
            self._oir_c_ovn = None

        if self._explicit_sub:
            sub_delete_query(
                self, self._dss, self._explicit_sub.id, self._explicit_sub.version
            )
            self._explicit_sub = None

        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        self._clean_workspace()
        self.end_cleanup()


def to_sub_ids(subscribers: list[SubscriberToNotify]) -> set[SubscriptionID]:
    """Flatten the passed list of subscribers to notify to a set of subscription IDs"""
    sub_ids = set()
    for subscriber in subscribers:
        for subscription in subscriber.subscriptions:
            sub_ids.add(subscription.subscription_id)

    return sub_ids
