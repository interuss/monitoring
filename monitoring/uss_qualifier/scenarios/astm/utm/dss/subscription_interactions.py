from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Set

from uas_standards.astm.f3548.v21.api import (
    Subscription,
    SubscriptionID,
    EntityID,
    OperationalIntentReference,
    OperationalIntentState,
    PutOperationalIntentReferenceParameters,
    SubscriberToNotify,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.delay import sleep
from monitoring.monitorlib.fetch import QueryError, Query
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
    DSSInstancesResource,
    DSSInstance,
)
from monitoring.uss_qualifier.resources.astm.f3548.v21.subscription_params import (
    SubscriptionParams,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    PendingCheck,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext

SUBSCRIPTION_EXPIRY_DELAY_SEC = 5
WAIT_FOR_EXPIRY_SEC = 7


class SubscriptionInteractions(TestScenario):
    """
    A scenario that tests interactions between subscriptions and entities across a DSS cluster.
    """

    SUB_TYPES = [
        register_resource_type(386, "First Subscription"),
        register_resource_type(387, "Second Subscription"),
    ]
    OIR_TYPE = register_resource_type(388, "Operational Intent References")

    _sub_ids: List[SubscriptionID]
    _oir_ids: List[EntityID]

    _current_subs: Dict[SubscriptionID, Subscription]
    _current_oirs: Dict[EntityID, OperationalIntentReference]

    # Times for the background subscriptions
    _sub_1_start: datetime
    _sub_1_end: datetime
    _sub_2_start: datetime
    _sub_2_end: datetime

    _manager: str

    def __init__(
        self,
        dss: DSSInstanceResource,
        other_instances: DSSInstancesResource,
        id_generator: IDGeneratorResource,
        planning_area: PlanningAreaResource,
        utm_client_identity: ClientIdentityResource,
    ):
        """
        Args:
            dss: primary dss to test
            other_instances: other dss instances to test
            id_generator: will let us generate specific identifiers
            planning_area: An Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.
        """
        super().__init__()
        scopes = {
            Scope.StrategicCoordination: "create and delete subscriptions and operational intents"
        }
        self._dss = dss.get_instance(scopes)
        self._pid = [self._dss.participant_id]
        self._planning_area = planning_area.specification

        self._secondary_instances = [
            dss.get_instance(scopes) for dss in other_instances.dss_instances
        ]

        # Prepare the two subscription ids:
        self._sub_ids = [
            id_generator.id_factory.make_id(sub_type) for sub_type in self.SUB_TYPES
        ]

        # Prepare one OIR id for each DSS we will interact with (one for the main and one for each secondary)
        base_oir_id = id_generator.id_factory.make_id(self.OIR_TYPE)
        self._oir_ids = [
            f"{base_oir_id[:-3]}{i:03d}"
            for i in range(len(self._secondary_instances) + 1)
        ]

        self._manager = utm_client_identity.subject()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self._setup_case()

        self.begin_test_case("OIR creation triggers relevant notifications")
        self._step_create_background_subs()
        self._steps_create_oirs_at_each_dss()
        self.end_test_case()

        self.end_test_scenario()

    def _step_create_background_subs(self):
        """Creates two subscription through the primary DSS: one that is valid from now into a short future,
        and one that starts one hour after the first ends"""

        # Create the first subscription
        self.begin_test_step("Create first background subscription")

        sub_now_params = self._planning_area.get_new_subscription_params(
            subscription_id=self._sub_ids[0],
            start_time=self._sub_1_start,
            duration=self._sub_1_end - self._sub_1_start,
            # This is a planning area without constraint processing
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )

        sub_now = self._create_sub_with_params(sub_now_params)
        self._current_subs[sub_now_params.sub_id] = sub_now
        self.end_test_step()

        # Create the second subscription, that starts later
        self.begin_test_step("Create second background subscription")

        sub_later_params = self._planning_area.get_new_subscription_params(
            subscription_id=self._sub_ids[1],
            start_time=self._sub_2_start,
            duration=self._sub_2_end - self._sub_2_start,
            # This is a planning area without constraint processing
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )

        sub_later = self._create_sub_with_params(sub_later_params)
        self._current_subs[sub_later_params.sub_id] = sub_later
        self.end_test_step()

    def _steps_create_oirs_at_each_dss(self):
        """Creates an OIR at each DSS instance"""

        common_params = self._planning_area.get_new_operational_intent_ref_params(
            key=[],  # Proper key added in each step below
            state=OperationalIntentState.Accepted,
            uss_base_url="https://example.interuss.org/oir_base_url",
            time_start=datetime.utcnow(),
            # Cover the first subscription's time, but not the second one
            time_end=self._sub_1_end + timedelta(minutes=10),
            subscription_id=None,
            implicit_sub_base_url="https://example.interuss.org/sub_base_url",
        )

        existing_oir = None
        possible_culprits = []
        for i, dss in enumerate([self._dss] + self._secondary_instances):

            self.begin_test_step("Create an OIR at every DSS in sequence")

            oir_id = self._oir_ids[i]

            if existing_oir:
                common_params.key.append(existing_oir.ovn)
            oir, subs, q = self._put_op_intent(dss, oir_id, common_params)
            notification_ids = _to_sub_ids(subs)
            possible_culprits.append(dss.participant_id)

            with self.check(
                "DSS response contains the expected background subscription",
                dss.participant_id,
            ) as check:
                if self._sub_ids[0] not in notification_ids:
                    check.record_failed(
                        summary="DSS did not return the intersecting background subscription",
                        details=f"Expected subscription {self._sub_ids[0]} (first background subscription) in the"
                        f" list of subscriptions to notify, but got {notification_ids}",
                        query_timestamps=[q.request.timestamp],
                    )

            with self.check(
                "DSS does not return non-intersecting background subscription",
                dss.participant_id,
            ) as check:
                if self._sub_ids[1] in notification_ids:
                    check.record_failed(
                        summary="DSS returned the non-intersecting background subscription",
                        details=f"Expected subscription {self._sub_ids[1]} (second background subscription) to not be in the"
                        f" list of subscriptions to notify, but got {notification_ids}",
                        query_timestamps=[q.request.timestamp],
                    )

            with self.check(
                "DSS returns the implicit subscriptions from intersecting OIRs",
                possible_culprits,
            ) as check:
                # Previously created OIRs have subscriptions that should be triggered:
                for existing_oir_id, existing_oir in self._current_oirs.items():
                    if existing_oir.subscription_id not in notification_ids:
                        check.record_failed(
                            summary="Missing subscription to notify",
                            details=f"Expected subscription {existing_oir.subscription_id} to be notified for "
                            f"freshly created OIR {existing_oir_id}",
                            query_timestamps=[q.request.timestamp],
                        )

            existing_oir = oir
            self._current_oirs[oir_id] = oir
            self.end_test_step()

    def _put_op_intent(
        self,
        dss: DSSInstance,
        oir_id: EntityID,
        params: PutOperationalIntentReferenceParameters,
    ) -> Tuple[OperationalIntentReference, List[SubscriberToNotify], Query]:

        with self.check(
            "Create operational intent reference query succeeds", [dss.participant_id]
        ) as check:
            try:
                oir, subs, q = dss.put_op_intent(
                    extents=params.extents,
                    key=params.key,
                    state=params.state,
                    base_url=params.uss_base_url,
                    oi_id=oir_id,
                    ovn=None,
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Failed to create operational intent reference",
                    details=f"Failed to create operational intent reference: {qe}",
                    query_timestamps=qe.query_timestamps,
                )

        return oir, subs, q

    def _create_sub_with_params(self, params: SubscriptionParams) -> Subscription:
        """Create a subscription with the given parameters via the primary DSS instance"""
        with self.check("Create subscription query succeeds") as check:
            r = self._dss.upsert_subscription(**params)
            if not r.success:
                check.record_failed(
                    summary="Create subscription query failed",
                    details=f"Failed to create a subscription on primary DSS with code {r.status_code}: {r.error_message}",
                    query_timestamps=[r.request.timestamp],
                )
        return r.subscription

    def _setup_case(self):
        self.begin_test_case("Setup")

        # First subscription from now to 20 minutes in the future
        self._sub_1_start = datetime.utcnow()
        self._sub_1_end = self._sub_1_start + timedelta(minutes=20)

        # Second subscription starts 20 minutes after the first ends and lasts for 1 hour
        self._sub_2_start = self._sub_1_end + timedelta(minutes=20)
        self._sub_2_end = self._sub_2_start + timedelta(hours=1)

        # Multiple runs of the scenario seem to rely on the same instance:
        # thus we need to reset the state of the scenario before running it.
        self._current_subs = {}
        self._current_oirs = {}

        self._ensure_clean_workspace_step()

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
        for oir_id in self._oir_ids:
            test_step_fragments.cleanup_op_intent(self, self._dss, oir_id)
        test_step_fragments.cleanup_active_subs(
            self,
            self._dss,
            extents,
        )
        for sub_id in self._sub_ids:
            test_step_fragments.cleanup_sub(self, self._dss, sub_id)

    def cleanup(self):
        self.begin_cleanup()
        self._clean_workspace()
        self.end_cleanup()


def _to_sub_ids(subscribers: List[SubscriberToNotify]) -> Set[SubscriptionID]:
    """Flatten the passed list of subscribers to notify to a set of subscription IDs"""
    sub_ids = set()
    for subscriber in subscribers:
        for subscription in subscriber.subscriptions:
            sub_ids.add(subscription.subscription_id)

    return sub_ids
