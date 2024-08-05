from datetime import datetime, timedelta, UTC
from typing import Dict, List

from uas_standards.astm.f3548.v21.api import (
    Subscription,
    SubscriptionID,
    EntityID,
    OperationalIntentReference,
    OperationalIntentState,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
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
from monitoring.uss_qualifier.scenarios.astm.utm.dss.subscription_interactions import (
    PER_DSS_OIR_TYPE,
    PER_DSS_SUB_TYPE,
    to_sub_ids,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class SubscriptionInteractionsDeletion(TestScenario):

    _oir_ids: List[EntityID]
    _sub_ids: List[SubscriptionID]

    _current_subs: Dict[SubscriptionID, Subscription]
    _current_oirs: Dict[EntityID, OperationalIntentReference]

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
        super().__init__()
        scopes = {
            Scope.StrategicCoordination: "create and delete subscriptions and operational intents"
        }
        self._dss = dss.get_instance(scopes)
        self._planning_area = planning_area.specification

        self._secondary_instances = [
            dss.get_instance(scopes) for dss in other_instances.dss_instances
        ]

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

        self.begin_test_case("Subscription deletion is reflected on all DSS instances")
        self._case_subs_deletion()
        self.end_test_case()

        self.begin_test_case(
            "OIR creation and modification does not trigger relevant notifications after subscription deletion"
        )
        self._case_create_modif_no_notifs()
        self.end_test_case()

        self.end_test_scenario()

    def _case_subs_deletion(self):
        self.begin_test_step("Create a subscription at every DSS in sequence")
        for i, dss in enumerate([self._dss] + self._secondary_instances):
            sub_id = self._sub_ids[i]
            sub_params = self._planning_area.get_new_subscription_params(
                subscription_id=sub_id,
                start_time=self._time_start,
                duration=self._time_end - self._time_start,
                notify_for_op_intents=True,
                notify_for_constraints=False,
            )
            _, _, sub = sub_create_query(self, self._dss, sub_params)
            self._current_subs[sub_id] = sub.subscription
        self.end_test_step()

        self.begin_test_step("Delete a subscription at every DSS in sequence")
        for i, dss in enumerate([self._dss] + self._secondary_instances):
            sub_id = self._sub_ids[i]

            with self.check(
                "Subscription can be deleted",
                [dss.participant_id],
            ) as check:
                del_sub = self._dss.delete_subscription(
                    sub_id, self._current_subs[sub_id].version
                )
                self.record_query(del_sub)
                if not del_sub.success:
                    check.record_failed(
                        summary="Delete subscription query failed",
                        details=f"Failed to delete a subscription on DSS instance with code {del_sub.status_code}: {del_sub.error_message}",
                        query_timestamps=[del_sub.request.timestamp],
                    )
            self._current_subs.pop(sub_id)

            for other_dss in {self._dss, *self._secondary_instances} - {dss}:
                with self.check(
                    "Get Subscription by ID",
                    [other_dss.participant_id],
                ) as check:
                    other_dss_sub = other_dss.get_subscription(sub_id)
                    self.record_query(other_dss_sub)
                    if not other_dss_sub.success:
                        check.record_failed(
                            summary="Get subscription query failed",
                            details=f"Failed to retrieved a subscription from DSS with code {other_dss_sub.status_code}: {other_dss_sub.error_message}",
                            query_timestamps=[other_dss_sub.request.timestamp],
                        )

                with self.check(
                    "Subscription does not exist on all other DSS instances",
                    [dss.participant_id, other_dss.participant_id],
                ) as check:
                    if other_dss_sub.status_code != 404:
                        check.record_failed(
                            summary="Subscription that was deleted on a DSS instance was found on another instance",
                            details=f"Subscription {other_dss_sub.subscription.id} deleted on DSS instance {dss.participant_id} was found on DSS instance {other_dss.participant_id}.",
                            query_timestamps=[other_dss_sub.request.timestamp],
                        )
        self.end_test_step()

    def _case_create_modif_no_notifs(self):
        self.begin_test_step("Create an OIR at every DSS in sequence")
        for i, dss in enumerate([self._dss] + self._secondary_instances):
            oir_id = self._oir_ids[i]
            oir = self._planning_area.get_new_operational_intent_ref_params(
                key=[current_oir.ovn for current_oir in self._current_oirs.values()],
                state=OperationalIntentState.Accepted,
                uss_base_url="https://example.interuss.org/oir_base_url",
                time_start=self._time_start,
                time_end=self._time_end,
                subscription_id=None,
                implicit_sub_base_url="https://example.interuss.org/sub_base_url",
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
            self._current_oirs[oir_id] = oir
            notification_ids = to_sub_ids(subs)

            with self.check(
                "DSS response does not contain the deleted subscriptions",
                dss.participant_id,
            ) as check:
                for sub_id in self._sub_ids:
                    if sub_id in notification_ids:
                        check.record_failed(
                            summary="DSS returned a deleted subscription to notify after creation of an OIR",
                            details=f"Expected subscription {sub_id} to not be amongst the list of subscriptions to notify, but got {notification_ids}",
                            query_timestamps=[q.request.timestamp],
                        )
        self.end_test_step()

        self.begin_test_step("Modify an OIR at every DSS in sequence")
        for i, dss in enumerate([self._dss] + self._secondary_instances):
            oir_id = self._oir_ids[i]
            oir = self._planning_area.get_new_operational_intent_ref_params(
                key=[current_oir.ovn for current_oir in self._current_oirs.values()],
                state=OperationalIntentState.Accepted,
                uss_base_url="https://example.interuss.org/oir_base_url_bis",  # dummy modification of the OIR
                time_start=self._time_start,
                time_end=self._time_end,
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

            self._current_oirs[oir_id] = oir
            notification_ids = to_sub_ids(subs)

            with self.check(
                "DSS response does not contain the deleted subscriptions",
                dss.participant_id,
            ) as check:
                for sub_id in self._sub_ids:
                    if sub_id in notification_ids:
                        check.record_failed(
                            summary="DSS returned a deleted subscription to notify after modification of an OIR",
                            details=f"Expected subscription {sub_id} to not be amongst the list of subscriptions to notify, but got {notification_ids}",
                            query_timestamps=[q.request.timestamp],
                        )
        self.end_test_step()

    def _setup_case(self):
        self.begin_test_case("Setup")

        self._time_start = datetime.now(UTC)
        self._time_end = self._time_start + timedelta(minutes=20)

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
