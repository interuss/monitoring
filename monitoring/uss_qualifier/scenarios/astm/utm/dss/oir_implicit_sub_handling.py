from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional

import arrow
from uas_standards.astm.f3548.v21.api import (
    Subscription,
    SubscriptionID,
    EntityID,
    OperationalIntentReference,
    OperationalIntentState,
    SubscriberToNotify,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext

OIR_A_TYPE = register_resource_type(391, "OIR for implicit sub handling")
OIR_B_TYPE = register_resource_type(392, "OIR for implicit sub handling")
OIR_C_TYPE = register_resource_type(393, "OIR for implicit sub handling")

TIME_TOLERANCE_SEC = 1


class OIRImplicitSubHandling(TestScenario):
    """
    A scenario that tests that a DSS properly handles the creation and mutation of implicit subscriptions
    """

    # Identifiers for the test OIRs
    _oir_a_id: str
    _oir_b_id: str
    _oir_c_id: str

    _oir_a_ovn: Optional[str]

    _current_subs: Dict[SubscriptionID, Subscription]
    _current_oirs: Dict[EntityID, OperationalIntentReference]

    # Reference times for the subscriptions and operational intents
    _time_0: datetime
    _time_1: datetime
    _time_2: datetime
    _time_3: datetime

    _manager: str

    # Keeps track of existing subscriptions in the planning area
    _initial_subscribers: List[SubscriberToNotify]
    _implicit_sub_1: Optional[Subscription]

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

        self._manager = utm_client_identity.subject()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self._setup_case()

        self.begin_test_case(
            "Single OIR implicit subscription is removed upon OIR deletion"
        )
        self.begin_test_step("Create an OIR with implicit subscription")
        self._step_create_single_oir()
        self.end_test_step()

        self.begin_test_step("Delete the OIR with implicit subscription")
        self._step_delete_single_oir()
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case(
            "Implicit subscriptions are mutated and reused when possible"
        )

        self.end_test_case()
        self.end_test_scenario()

    def _step_create_single_oir(self):
        with self.check(
            "Create operational intent reference query succeeds", self._pid
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
                    base_url="example.interuss.org/uss_base",
                    oi_id=self._oir_a_id,
                    ovn=None,
                    subscription_id=None,
                )
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="OIR Creation failed",
                    details=str(e),
                    query_timestamps=e.query_timestamps,
                )

        # Keep track of any subscription already existing in the area
        self._initial_subscribers = subs
        self._oir_a_ovn = oir.ovn

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
                    sub.subscription.time_start.value.datetime - self._time_2
                ).total_seconds()
                > TIME_TOLERANCE_SEC
            ):
                check.record_failed(
                    summary="Subscription time_start does not match OIR",
                    details=f"Subscription time_start is {sub.subscription.time_start.value.datetime}, expected {self._time_2}",
                    query_timestamps=[sub.request.timestamp],
                )
            if (
                abs(
                    sub.subscription.time_end.value.datetime - self._time_3
                ).total_seconds()
                > TIME_TOLERANCE_SEC
            ):
                check.record_failed(
                    summary="Subscription time_start does not match OIR",
                    details=f"Subscription time_start is {sub.subscription.time_start.value.datetime}, expected {self._time_2}",
                    query_timestamps=[sub.request.timestamp],
                )

        self._implicit_sub_1 = sub.subscription

    def _step_delete_single_oir(self):

        with self.check(
            "Delete operational intent reference query succeeds", self._pid
        ) as check:
            try:
                deleted_oir, subs, q = self._dss.delete_op_intent(
                    self._oir_a_id, self._oir_a_ovn
                )
                self.record_query(q)
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
            if non_existing_sub.success:
                check.record_failed(
                    summary="Subscription still exists",
                    details=f"Subscription {self._implicit_sub_1.id} is still returned, while it was expected to not be found.",
                    query_timestamps=[non_existing_sub.request.timestamp],
                )
            elif non_existing_sub.response.status_code != 404:
                check.record_failed(
                    summary=f"Unexpected error code: {non_existing_sub.response.status_code}",
                    details=f"Querying subscription {self._implicit_sub_1.subscription_id}, which is not expected to exist, should result in an HTTP 404 error. Got {non_existing_sub.response.status_code} instead.",
                    query_timestamps=[non_existing_sub.request.timestamp],
                )

    # TODO validate subs are as before?

    def _setup_case(self):
        self.begin_test_case("Setup")

        # T0 corresponds to 'now'
        self._time_0 = arrow.utcnow().datetime

        # T1, T2 and T3 are chronologically ordered and relatively far from T0
        self._time_1 = self._time_0 + timedelta(hours=20)
        self._time_2 = self._time_1 + timedelta(hours=1)
        self._time_3 = self._time_2 + timedelta(hours=1)

        self._ensure_clean_workspace_step()

        self._initial_subscribers = []
        self._implicit_sub_1 = None

        self.end_test_case()

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

    def cleanup(self):
        self.begin_cleanup()
        self._clean_workspace()
        self.end_cleanup()


def to_sub_ids(subscribers: List[SubscriberToNotify]) -> Set[SubscriptionID]:
    """Flatten the passed list of subscribers to notify to a set of subscription IDs"""
    sub_ids = set()
    for subscriber in subscribers:
        for subscription in subscriber.subscriptions:
            sub_ids.add(subscription.subscription_id)

    return sub_ids
