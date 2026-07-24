import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from functools import partial
from random import Random
from threading import Lock
from typing import Any

import uuid6
from loguru import logger
from uas_standards.astm.f3548.v21 import api
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.benchmarker.configurations.user.astm.dss import ASTMDSSSelectionStrategy
from monitoring.benchmarker.configurations.user.astm.scd import (
    BehaviorSpecification,
    OpIntentRefCleanupStrategy,
    OpIntentRefCreationStrategy,
    SubscriptionStrategy,
)
from monitoring.benchmarker.engine.coordination import (
    CoordinationGroupID,
    CoordinationMessage,
    CoordinationSubscriber,
)
from monitoring.benchmarker.engine.users.flight_planner.framework import (
    CompletedFlightAction,
    Flight,
    FlightAction,
    FlightActionType,
    FlightID,
)
from monitoring.benchmarker.engine.users.framework import VirtualUser
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DSSInstanceResource,
    DSSInstancesResource,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID

COORDINATION_SUBJECT_ADD_OVN = "enging.users.flight_planner.scd.add_ovn"
COORDINATION_SUBJECT_REMOVE_OVN = "enging.users.flight_planner.scd.remove_ovn"


class SCDHandler(CoordinationSubscriber):
    user: VirtualUser

    dss_instances: list[DSSInstance]
    dss_selection_strategy: ASTMDSSSelectionStrategy

    subscription_strategy: SubscriptionStrategy

    op_intent_ref_creation_strategy: OpIntentRefCreationStrategy
    """All fields guaranteed to be present."""

    op_intent_ref_cleanup_strategy: OpIntentRefCleanupStrategy
    """All fields guaranteed to be present."""

    random: Random

    subscription_checked: bool = False
    op_intent_refs: dict[FlightID, api.OperationalIntentReference]

    key: list[api.EntityOVN]
    """OVNs currently known by this user."""

    key_lock: Lock
    """Guards `key` access, coordinating between all the different users communicating OVNs."""

    def __init__(
        self,
        behavior: BehaviorSpecification,
        resource_pool: dict[ResourceID, Any],
        user: VirtualUser,
    ):
        self.user = user

        self.key = []
        self.key_lock = Lock()

        self.dss_instances = []
        scopes_required = {
            Scope.StrategicCoordination.value: "sharing operational intents for flights to provide strategic conflict detection",
        }
        for res_id in behavior.dss_pool:
            if res_id not in resource_pool:
                raise ValueError(
                    f"Resource '{res_id}' in scd_behavior.dss_pool not found in resource pool"
                )
            res = resource_pool[res_id]
            if isinstance(res, DSSInstancesResource):
                for dss_instance_res in res.dss_instances:
                    self.dss_instances.append(
                        dss_instance_res.get_instance(scopes_required)
                    )
            elif isinstance(res, DSSInstanceResource):
                self.dss_instances.append(res.get_instance(scopes_required))
            else:
                raise ValueError(
                    f"Resource '{res_id}' is not a uss_qualifier.resources.astm.f3548.v21.dss.DSSInstanceResource nor uss_qualifier.resources.astm.f3548.v21.dss.DSSInstancesResource"
                )

        if not self.dss_instances:
            raise ValueError(
                f"No SCD DSS instances resolved from scd_behavior.dss_pool for user '{user.user_id}'"
            )

        if len(self.dss_instances) > 1:
            if "dss_selection_strategy" in behavior and behavior.dss_selection_strategy:
                self.dss_selection_strategy = behavior.dss_selection_strategy
            else:
                raise ValueError(
                    f"User `{user.user_id}` specified {len(self.dss_instances)} DSS instances but no dss_selection strategy"
                )
        else:
            self.dss_selection_strategy = ASTMDSSSelectionStrategy.First

        if self.dss_selection_strategy not in (
            ASTMDSSSelectionStrategy.First,
            ASTMDSSSelectionStrategy.Random,
        ):
            raise NotImplementedError(
                f"DSS selection strategy '{self.dss_selection_strategy}' not implemented"
            )

        self.subscription_strategy = SubscriptionStrategy(
            **behavior.subscription_strategy
        )
        if "single_subscription" not in self.subscription_strategy:
            self.subscription_strategy.single_subscription = None
        if "implicit_subscription" not in self.subscription_strategy:
            self.subscription_strategy.implicit_subscription = None

        self.op_intent_ref_creation_strategy = behavior.op_intent_ref_creation_strategy

        self.op_intent_ref_cleanup_strategy = behavior.op_intent_ref_cleanup_strategy

        self.random = Random()

        self.op_intent_refs = {}

        if (
            "ovn_coordination_group" in self.op_intent_ref_creation_strategy
            and self.op_intent_ref_creation_strategy.ovn_coordination_group
        ):
            self.user.coordinator.subscribe(
                self, self.op_intent_ref_creation_strategy.ovn_coordination_group
            )

    def receive_coordination_message(self, msg: CoordinationMessage) -> None:
        if msg.subject == COORDINATION_SUBJECT_ADD_OVN:
            if not isinstance(msg.content, api.EntityOVN):
                raise RuntimeError(
                    f"Expected an EntityOVN content in a CoordinationMessage with subject {msg.subject} but instead found a {type(msg.content).__name__}"
                )
            with self.key_lock:
                self.key.append(msg.content)
        elif msg.subject == COORDINATION_SUBJECT_REMOVE_OVN:
            if not isinstance(msg.content, api.EntityOVN):
                raise RuntimeError(
                    f"Expected an EntityOVN content in a CoordinationMessage with subject {msg.subject} but instead found a {type(msg.content).__name__}"
                )
            with self.key_lock:
                self.key.remove(msg.content)

    def select_dss_instance(self) -> DSSInstance:
        if self.dss_selection_strategy == ASTMDSSSelectionStrategy.First:
            return self.dss_instances[0]
        elif self.dss_selection_strategy == ASTMDSSSelectionStrategy.Random:
            return self.random.choice(self.dss_instances)
        else:
            raise NotImplementedError(
                f"Unsupported DSS selection strategy `{self.dss_selection_strategy}`"
            )

    def get_utm_actions(self, flight: Flight) -> Iterable[FlightAction]:
        if (
            not self.subscription_checked
            and "single_subscription" in self.subscription_strategy
            and self.subscription_strategy.single_subscription
        ):
            yield FlightAction(
                timestamp=datetime.now(UTC),
                start=partial(
                    self.ensure_subscription_exists,
                    flight,
                    self.subscription_strategy.single_subscription.subscription_id,
                ),
                run_on_shutdown=False,
            )
        else:
            yield from self.get_create_actions(flight)

    async def ensure_subscription_exists(
        self,
        flight: Flight,
        subscription_id: api.SubscriptionID,
    ) -> list[FlightAction]:
        t0 = datetime.now(UTC)
        if not self.subscription_strategy.single_subscription:
            raise RuntimeError(
                "ensure_subscription_exists called even though single_subscription was undefined"
            )

        start_time = t0
        end_time = (
            t0 + self.subscription_strategy.single_subscription.duration.timedelta
        )
        area = self.subscription_strategy.single_subscription.area.to_latlngrect()
        min_alt = self.subscription_strategy.single_subscription.min_alt.to_w84_m()
        max_alt = self.subscription_strategy.single_subscription.max_alt.to_w84_m()

        dss_instance = self.select_dss_instance()
        uss_base_url = make_fake_url()

        mutated_sub = dss_instance.upsert_subscription(
            area_vertices=area,
            start_time=start_time,
            end_time=end_time,
            base_url=uss_base_url,
            sub_id=subscription_id,
            notify_for_op_intents=True,
            notify_for_constraints=False,
            min_alt_m=min_alt,
            max_alt_m=max_alt,
        )
        success = None
        self.user.record_query(mutated_sub, True)

        if mutated_sub.status_code == 409:
            # Subscription already exists
            success = True

        if success is None and not mutated_sub.success:
            success = False

        if success is None:
            try:
                _ = mutated_sub.subscription
                success = True
            except ValueError:
                success = False

        flight.completed_actions.append(
            CompletedFlightAction(
                type=FlightActionType.UpsertSCDSubscription,
                initiated_at=t0,
                causes_flight_failure=not success,
            )
        )
        self.subscription_checked = True
        if success:
            return list(self.get_create_actions(flight))
        else:
            return []

    def get_create_actions(self, flight: Flight) -> Iterable[FlightAction]:
        op_intent_id = api.EntityID(uuid.uuid4())

        if (
            "accept_before_flight_start" in self.op_intent_ref_creation_strategy
            and self.op_intent_ref_creation_strategy.accept_before_flight_start
        ):
            yield FlightAction(
                timestamp=flight.start_time
                - self.op_intent_ref_creation_strategy.accept_before_flight_start.timedelta,
                flight_id=flight.id,
                start=partial(
                    self.upsert_op_intent_ref,
                    flight,
                    op_intent_id,
                    api.OperationalIntentState.Accepted,
                ),
                run_on_shutdown=False,
            )

        if (
            "activate_before_flight_start" in self.op_intent_ref_creation_strategy
            and self.op_intent_ref_creation_strategy.activate_before_flight_start
        ):
            yield FlightAction(
                timestamp=flight.start_time
                - self.op_intent_ref_creation_strategy.activate_before_flight_start.timedelta,
                flight_id=flight.id,
                start=partial(
                    self.upsert_op_intent_ref,
                    flight,
                    op_intent_id,
                    api.OperationalIntentState.Activated,
                ),
                run_on_shutdown=False,
            )

    async def upsert_op_intent_ref(
        self,
        flight: Flight,
        op_intent_id: api.EntityID,
        state: api.OperationalIntentState,
    ) -> list[FlightAction]:
        t0 = datetime.now(UTC)

        if state not in (
            api.OperationalIntentState.Accepted,
            api.OperationalIntentState.Activated,
        ):
            raise NotImplementedError(f"Cannot transition op intent to state {state}")

        dss_instance = self.select_dss_instance()
        uss_base_url = make_fake_url()
        coordination_group = (
            self.op_intent_ref_creation_strategy.ovn_coordination_group
            if "ovn_coordination_group" in self.op_intent_ref_creation_strategy
            and self.op_intent_ref_creation_strategy.ovn_coordination_group
            else None
        )

        kwargs = {}
        if self.subscription_strategy.single_subscription:
            kwargs["subscription_id"] = (
                self.subscription_strategy.single_subscription.subscription_id
            )
        elif self.subscription_strategy.implicit_subscription:
            pass
        else:
            raise ValueError(
                f"No valid subscription strategy specified in scd_behavior.subscription_strategy for user `{self.user.user_id}`"
            )

        op_intent_ref = self.op_intent_refs.get(flight.id, None)
        old_ovn = op_intent_ref.ovn if op_intent_ref else None
        ovn_suffix = None
        requested_ovn = None

        attempts = 1
        if (
            "retries" in self.op_intent_ref_creation_strategy
            and self.op_intent_ref_creation_strategy.retries
        ):
            attempts += self.op_intent_ref_creation_strategy.retries
        success = False
        for attempt in range(attempts):
            if (
                "coordinate_requested_ovns" in self.op_intent_ref_creation_strategy
                and self.op_intent_ref_creation_strategy.coordinate_requested_ovns
            ):
                ovn_suffix = str(uuid6.uuid7())
                requested_ovn = api.EntityOVN(f"{op_intent_id}_{ovn_suffix}")
                if coordination_group:
                    self.user.coordinator.publish(
                        coordination_group,
                        COORDINATION_SUBJECT_ADD_OVN,
                        requested_ovn,
                    )

            with self.key_lock:
                key = list(self.key)

            try:
                # TODO: upsert op intent asynchronously
                op_intent_ref, _, query = await self.user.run_sync_client_call(
                    dss_instance.put_op_intent,
                    extents=flight.volumes.to_f3548v21(),
                    key=key,
                    state=state,
                    base_url=uss_base_url,
                    oi_id=op_intent_id,
                    ovn=old_ovn,
                    requested_ovn_suffix=ovn_suffix,
                    **kwargs,
                )
                self.user.record_query(query)
                success = True
                break
            except QueryError as e:
                for q in e.queries:
                    self.user.record_query(q)
                    if q.status_code == 409 and q.response.json:
                        missing_op_intents = q.response.json.get(
                            "missing_operational_intents"
                        )
                        if missing_op_intents:
                            logger.warning(
                                f"{self.user.user_id} missing OVNs for OI {op_intent_id}:\n"
                                + "\n".join(
                                    f"OI {oi.get('id', None)}: OVN {oi.get('ovn', None)}"
                                    for oi in missing_op_intents
                                )
                            )
                flight.completed_actions.append(
                    CompletedFlightAction(
                        type=FlightActionType.UpsertOpIntent,
                        initiated_at=t0,
                        causes_flight_failure=attempt >= attempts - 1,
                    )
                )
                t0 = datetime.now(UTC)
                if requested_ovn and coordination_group:
                    self.user.coordinator.publish(
                        coordination_group,
                        COORDINATION_SUBJECT_REMOVE_OVN,
                        requested_ovn,
                    )

        if not success:
            return []

        if op_intent_ref is None:
            raise RuntimeError(
                "op_intent_ref cannot be None upon successful op intent ref upsertion"
            )

        flight.completed_actions.append(
            CompletedFlightAction(
                type=FlightActionType.UpsertOpIntent,
                initiated_at=t0,
                causes_flight_failure=False,
            )
        )
        self.op_intent_refs[flight.id] = op_intent_ref

        # Notify other coordinating users
        if coordination_group:
            if op_intent_ref.ovn != old_ovn and op_intent_ref.ovn != requested_ovn:
                self.user.coordinator.publish(
                    coordination_group,
                    COORDINATION_SUBJECT_ADD_OVN,
                    op_intent_ref.ovn,
                )
            if old_ovn and op_intent_ref.ovn != old_ovn:
                self.user.coordinator.publish(
                    coordination_group,
                    COORDINATION_SUBJECT_REMOVE_OVN,
                    old_ovn,
                )
            if requested_ovn and op_intent_ref.ovn != requested_ovn:
                logger.warning(
                    f"Requested OVN {requested_ovn} was not accepted; returned {op_intent_ref.ovn} instead for user {self.user.user_id}"
                )
                self.user.coordinator.publish(
                    coordination_group,
                    COORDINATION_SUBJECT_REMOVE_OVN,
                    requested_ovn,
                )
        else:
            if old_ovn and op_intent_ref.ovn != old_ovn:
                self.receive_coordination_message(
                    CoordinationMessage(
                        group_id=None,
                        subject=COORDINATION_SUBJECT_REMOVE_OVN,
                        content=op_intent_ref.ovn,
                    )
                )
            if old_ovn is None or op_intent_ref.ovn != old_ovn:
                self.receive_coordination_message(
                    CoordinationMessage(
                        group_id=None,
                        subject=COORDINATION_SUBJECT_ADD_OVN,
                        content=op_intent_ref.ovn,
                    )
                )

        return list(self.get_delete_actions(flight, op_intent_id))

    def get_delete_actions(
        self, flight: Flight, op_intent_id: api.EntityID
    ) -> Iterable[FlightAction]:
        deletion_time = None
        if (
            "after_actual_flight_end" in self.op_intent_ref_cleanup_strategy
            and self.op_intent_ref_cleanup_strategy.after_actual_flight_end
        ):
            deletion_time = (
                flight.actual_end_time
                + self.op_intent_ref_cleanup_strategy.after_actual_flight_end.timedelta
            )
        if (
            "after_planned_flight_end" in self.op_intent_ref_cleanup_strategy
            and self.op_intent_ref_cleanup_strategy.after_planned_flight_end
        ):
            new_time = (
                flight.volumes.time_end_not_none.datetime
                + self.op_intent_ref_cleanup_strategy.after_planned_flight_end.timedelta
            )
            deletion_time = (
                new_time if deletion_time is None else max(deletion_time, new_time)
            )
        if deletion_time is not None:
            yield FlightAction(
                timestamp=deletion_time,
                flight_id=flight.id,
                start=partial(
                    self.delete_op_intent_ref,
                    flight,
                    op_intent_id,
                ),
                run_on_shutdown=True,
            )

    async def delete_op_intent_ref(
        self, flight: Flight, op_intent_id: api.EntityID
    ) -> list[FlightAction]:
        t0 = datetime.now(UTC)
        dss_instance = self.select_dss_instance()

        with self.key_lock:
            op_intent_ref = self.op_intent_refs.pop(flight.id, None)

        if op_intent_ref:
            # TODO: delete op intent ref asynchronously
            _, _, query = await self.user.run_sync_client_call(
                dss_instance.delete_op_intent,
                id=op_intent_id,
                ovn=op_intent_ref.ovn,
            )

            success = query.status_code == 200
            self.user.record_query(query, success)
            flight.completed_actions.append(
                CompletedFlightAction(
                    type=FlightActionType.DeleteOpIntent,
                    initiated_at=t0,
                    causes_flight_failure=not success,
                )
            )

            if (
                "ovn_coordination_group" in self.op_intent_ref_creation_strategy
                and self.op_intent_ref_creation_strategy.ovn_coordination_group
            ):
                self.user.coordinator.publish(
                    self.op_intent_ref_creation_strategy.ovn_coordination_group,
                    COORDINATION_SUBJECT_REMOVE_OVN,
                    op_intent_ref.ovn,
                )
            else:
                self.receive_coordination_message(
                    CoordinationMessage(
                        group_id=None,
                        subject=COORDINATION_SUBJECT_REMOVE_OVN,
                        content=op_intent_ref.ovn,
                    )
                )

        return []

    @staticmethod
    def enumerate_coordination_groups(
        behavior: BehaviorSpecification,
    ) -> Iterable[CoordinationGroupID]:
        if (
            "ovn_coordination_group" in behavior.op_intent_ref_creation_strategy
            and behavior.op_intent_ref_creation_strategy.ovn_coordination_group
        ):
            yield behavior.op_intent_ref_creation_strategy.ovn_coordination_group
