from datetime import UTC, datetime, timedelta
from typing import Dict, List, Set

from uas_standards.astm.f3548.v21.api import (
    EntityID,
    OperationalIntentReference,
    OperationalIntentState,
    SubscriberToNotify,
    Subscription,
    SubscriptionID,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.delay import sleep
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.temporal import Time
from monitoring.monitorlib.testing import make_fake_url
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
    DSSInstancesResource,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.sub.crud import (
    sub_create_query,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

SUBSCRIPTION_EXPIRY_DELAY_SEC = 5
WAIT_FOR_EXPIRY_SEC = 7

BG_SUB_TYPE = register_resource_type(386, "Background subscription")
PER_DSS_OIR_TYPE = register_resource_type(387, "Multiple Operational Intent References")
PER_DSS_SUB_TYPE = register_resource_type(388, "Multiple Subscriptions")


class SubscriptionInteractions(TestScenario):
    """
    A scenario that tests interactions between subscriptions and entities across a DSS cluster.
    """

    _background_sub_id: SubscriptionID

    _oir_ids: List[EntityID]
    _sub_ids: List[SubscriptionID]

    _current_subs: Dict[SubscriptionID, Subscription]
    _current_oirs: Dict[EntityID, OperationalIntentReference]

    # Reference times for the subscriptions and operational intents
    _time_start: datetime
    _time_end: datetime

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

        # Prepare the background subscription id
        self._background_sub_id = id_generator.id_factory.make_id(BG_SUB_TYPE)

        # Prepare one OIR id for each DSS we will interact with (one for the main and one for each secondary)
        base_oir_id = id_generator.id_factory.make_id(PER_DSS_OIR_TYPE)
        self._oir_ids = [
            f"{base_oir_id[:-3]}{i:03d}"
            for i in range(len(self._secondary_instances) + 1)
        ]
        # Prepare one subscription id for each DSS we will interact with (one for the main and one for each secondary)
        base_sub_id = id_generator.id_factory.make_id(PER_DSS_SUB_TYPE)
        self._sub_ids = [
            f"{base_sub_id[:-3]}{i:03d}"
            for i in range(len(self._secondary_instances) + 1)
        ]

        self._manager = utm_client_identity.subject()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self._setup_case()

        self.begin_test_case(
            "OIR creation and modification trigger relevant notifications"
        )
        self._step_create_background_sub()
        self._steps_create_oirs_at_each_dss()
        self.end_test_case()

        self.begin_test_case("Subscription creation returns relevant OIRs")
        self._steps_create_subs_at_each_dss()
        self.end_test_case()

        self.begin_test_case("Expiration of subscriptions removes them")
        self._steps_expire_subs_at_each_dss()
        self.end_test_case()
        self.end_test_scenario()

    def _step_create_background_sub(self):
        self.begin_test_step("Create background subscription")

        sub_now_params = self._planning_area.get_new_subscription_params(
            subscription_id=self._background_sub_id,
            start_time=self._time_start,
            duration=self._time_end - self._time_start,
            # This is a planning area without constraint processing
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )

        sub_now, _, _ = sub_create_query(self, self._dss, sub_now_params)
        self._current_subs[sub_now_params.sub_id] = sub_now
        self.end_test_step()

    def _steps_create_oirs_at_each_dss(self):
        """Creates an OIR at each DSS instance"""

        def _expected_subs_check(
            _participant: ParticipantID,
            _notif_ids: set[str],
            _query_timestamp: datetime,
        ):
            with self.check(
                "DSS response contains the expected background subscription",
                _participant,
            ) as _check:
                if self._background_sub_id not in _notif_ids:
                    _check.record_failed(
                        summary="DSS did not return the intersecting background subscription",
                        details=f"Expected subscription {self._background_sub_id} (background subscription) in the"
                        f" list of subscriptions to notify, but got {_notif_ids}",
                        query_timestamps=[_query_timestamp],
                    )

        def _implicit_subs_check(
            _participants: List[ParticipantID],
            _notif_ids: set[str],
            _query_timestamp: datetime,
        ):
            # TODO: the participants of this check should be only the subscription owner and the DSS that returned the subscription
            with self.check(
                "DSS returns the implicit subscriptions from intersecting OIRs",
                _participants,
            ) as _check:
                # Previously created OIRs have subscriptions that should be triggered:
                for existing_oir_id, existing_oir in self._current_oirs.items():
                    if existing_oir.subscription_id not in _notif_ids:
                        _check.record_failed(
                            summary="Missing subscription to notify",
                            details=f"Expected subscription {existing_oir.subscription_id} to be notified for "
                            f"freshly created OIR {existing_oir_id}",
                            query_timestamps=[_query_timestamp],
                        )

        self.begin_test_step("Create an OIR at every DSS in sequence")
        possible_culprits: List[ParticipantID] = []
        for i, dss in enumerate([self._dss] + self._secondary_instances):
            oir_id = self._oir_ids[i]
            oir = self._planning_area.get_new_operational_intent_ref_params(
                key=[current_oir.ovn for current_oir in self._current_oirs.values()],
                state=OperationalIntentState.Accepted,
                uss_base_url=make_fake_url("oir_base_url"),
                time_start=datetime.now(UTC),
                time_end=self._time_end + timedelta(minutes=10),
                subscription_id=None,
                implicit_sub_base_url=make_fake_url("sub_base_url"),
            )

            with self.check(
                "Create operational intent reference query succeeds",
                [dss.participant_id],
            ) as check:
                try:
                    oir, subs, q = dss.put_op_intent(
                        extents=oir.extents,
                        key=oir.key,
                        state=oir.state,
                        base_url=oir.uss_base_url,
                        oi_id=oir_id,
                    )
                    self.record_query(q)
                except QueryError as qe:
                    self.record_queries(qe.queries)
                    check.record_failed(
                        summary="Failed to create operational intent reference",
                        details=f"Failed to create operational intent reference: {qe}",
                        query_timestamps=qe.query_timestamps,
                    )

            notification_ids = to_sub_ids(subs)
            possible_culprits.append(dss.participant_id)

            _expected_subs_check(
                dss.participant_id, notification_ids, q.request.timestamp
            )
            _implicit_subs_check(
                possible_culprits, notification_ids, q.request.timestamp
            )

            self._current_oirs[oir_id] = oir
        self.end_test_step()

        self.begin_test_step("Modify an OIR at every DSS in sequence")
        for i, dss in enumerate([self._dss] + self._secondary_instances):
            oir_id = self._oir_ids[i]
            oir = self._planning_area.get_new_operational_intent_ref_params(
                key=[current_oir.ovn for current_oir in self._current_oirs.values()],
                state=OperationalIntentState.Accepted,
                uss_base_url=make_fake_url(
                    "oir_base_url_bis"
                ),  # dummy modification of the OIR
                time_start=datetime.now(UTC),
                time_end=self._time_end + timedelta(minutes=10),
                subscription_id=self._current_oirs[oir_id].subscription_id,
            )

            with self.check(
                "Mutate operational intent reference query succeeds",
                [dss.participant_id],
            ) as check:
                try:
                    oir, subs, q = dss.put_op_intent(
                        extents=oir.extents,
                        key=oir.key,
                        state=oir.state,
                        base_url=oir.uss_base_url,
                        oi_id=oir_id,
                        ovn=self._current_oirs[oir_id].ovn,
                        subscription_id=oir.subscription_id,
                    )
                    self.record_query(q)
                except QueryError as qe:
                    self.record_queries(qe.queries)
                    check.record_failed(
                        summary="Failed to mutate operational intent reference",
                        details=f"Failed to mutate operational intent reference: {qe}",
                        query_timestamps=qe.query_timestamps,
                    )

            notification_ids = to_sub_ids(subs)

            _expected_subs_check(
                dss.participant_id, notification_ids, q.request.timestamp
            )
            _implicit_subs_check(
                [self._dss.participant_id]
                + [sec_dss.participant_id for sec_dss in self._secondary_instances],
                notification_ids,
                q.request.timestamp,
            )

            self._current_oirs[oir_id] = oir
        self.end_test_step()

    def _steps_create_subs_at_each_dss(self):
        """Creates a subscription at each DSS instance"""

        common_params = self._planning_area.get_new_subscription_params(
            subscription_id="",
            start_time=self._time_start,
            duration=self._time_end - self._time_start,
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )

        # All previously created OIRs are relevant to each subscription
        expected_oir_ids = set(self._oir_ids)

        for i, dss in enumerate([self._dss] + self._secondary_instances):
            self.begin_test_step("Create a subscription at every DSS in sequence")

            sub_id = self._sub_ids[i]
            common_params.sub_id = sub_id
            sub, oirs, r = sub_create_query(self, self._dss, common_params)
            self._current_subs[sub_id] = sub

            returned_oir_ids = set(oir.id for oir in oirs)

            with self.check(
                "DSS response contains the expected OIRs",
                dss.participant_id,
            ) as check:
                if not expected_oir_ids.issubset(returned_oir_ids):
                    missing_oirs = expected_oir_ids - returned_oir_ids
                    check.record_failed(
                        summary="DSS did not return the expected OIRs",
                        details=f"Expected OIRs {expected_oir_ids} in the list of OIRs to notify, but got {returned_oir_ids}. "
                        f"Missing: {missing_oirs}",
                        query_timestamps=[r.request.timestamp],
                    )

            for other_dss in {self._dss, *self._secondary_instances} - {dss}:
                other_dss_sub = other_dss.get_subscription(sub_id)
                self.record_query(other_dss_sub)
                with self.check(
                    "Get Subscription by ID",
                    other_dss.participant_id,
                ) as check:
                    if not (other_dss_sub.success or other_dss_sub.was_not_found):
                        check.record_failed(
                            summary="Get subscription query failed",
                            details=f"Failed to retrieved a subscription from DSS with code {other_dss_sub.status_code}: {other_dss_sub.error_message}",
                            query_timestamps=[other_dss_sub.request.timestamp],
                        )

                with self.check(
                    "Subscription may be retrieved from all other DSS instances",
                    [dss.participant_id, other_dss.participant_id],
                ) as check:
                    # status may have been 404
                    if other_dss_sub.status_code != 200:
                        check.record_failed(
                            summary="Subscription created on a DSS instance was not found on another instance",
                            details=f"Subscription {sub_id} created on DSS instance {dss.participant_id} was not found on DSS instance {other_dss.participant_id} (error message: {other_dss_sub.error_message}).",
                            query_timestamps=[other_dss_sub.request.timestamp],
                        )

            self.end_test_step()

    def _steps_expire_subs_at_each_dss(self):
        self.begin_test_step("Expire explicit subscriptions at every DSS in sequence")
        for i, dss in enumerate([self._dss] + self._secondary_instances):
            sub_id = self._sub_ids[i]
            sub_params = self._planning_area.get_new_subscription_params(
                subscription_id=sub_id,
                start_time=datetime.now(UTC),
                duration=timedelta(seconds=SUBSCRIPTION_EXPIRY_DELAY_SEC),
                notify_for_op_intents=True,
                notify_for_constraints=False,
            )

            with self.check(
                "Subscription can be mutated",
                [dss.participant_id],
            ) as check:
                sub = self._dss.upsert_subscription(
                    **sub_params,
                    version=self._current_subs[sub_id].version,
                )
                self.record_query(sub)
                if not sub.success:
                    check.record_failed(
                        summary="Update subscription query failed",
                        details=f"Failed to update a subscription on DSS instance with code {sub.status_code}: {sub.error_message}",
                        query_timestamps=[sub.request.timestamp],
                    )
            self._current_subs.pop(sub_id)

        sleep(
            timedelta(seconds=WAIT_FOR_EXPIRY_SEC),
            "waiting for subscriptions to expire",
        )

        for i, dss in enumerate([self._dss] + self._secondary_instances):
            sub_id = self._sub_ids[i]
            for other_dss in {self._dss, *self._secondary_instances} - {dss}:
                other_dss_subs = other_dss.query_subscriptions(
                    Volume4D(
                        volume=self._planning_area.volume,
                        time_start=Time(self._time_start),
                        time_end=Time(self._time_end),
                    ).to_f3548v21()
                )
                self.record_query(other_dss_subs)

                with self.check(
                    "Successful subscription search query",
                    dss.participant_id,
                ) as check:
                    if not other_dss_subs.success:
                        check.record_failed(
                            summary="Search subscriptions query failed",
                            details=f"Failed to search for subscriptions from DSS with code {other_dss_subs.status_code}: {other_dss_subs.error_message}",
                            query_timestamps=[other_dss_subs.request.timestamp],
                        )

                with self.check(
                    "Subscription does not exist on all other DSS instances",
                    [dss.participant_id, other_dss.participant_id],
                ) as check:
                    if sub_id in other_dss_subs.subscriptions:
                        check.record_failed(
                            summary="Subscription that expired on a DSS instance was found on another instance",
                            details=f"Subscription {sub_id} expired on DSS instance {dss.participant_id} was found on DSS instance {other_dss.participant_id}.",
                            query_timestamps=[other_dss_subs.request.timestamp],
                        )

        self.end_test_step()

    def _setup_case(self):
        self.begin_test_case("Setup")

        # Subscription from now to 20 minutes in the future
        self._time_start = datetime.now(UTC)
        self._time_end = self._time_start + timedelta(minutes=20)

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
        test_step_fragments.cleanup_sub(self, self._dss, self._background_sub_id)
        for sub_id in self._sub_ids:
            test_step_fragments.cleanup_sub(self, self._dss, sub_id)

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
