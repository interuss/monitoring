import asyncio
import heapq
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from functools import partial
from random import Random
from typing import Any

import s2sphere
from loguru import logger

from monitoring.benchmarker.configurations.users import (
    ASTMDSSSelectionStrategy,
    BenchmarkUserSpecification,
    NetRIDObserverBehaviorSpecification,
    S2GriddedSubscriptionStrategySpecification,
)
from monitoring.benchmarker.engine.coordination import Coordinator
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.engine.users.framework import Action, VirtualUser
from monitoring.monitorlib.fetch.rid import Subscription
from monitoring.monitorlib.geo import EARTH_RADIUS_M
from monitoring.monitorlib.mutate.rid import delete_subscription, upsert_subscription
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources.astm.f3411.dss import (
    DSSInstance,
    DSSInstanceResource,
    DSSInstancesResource,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID

SUBSCRIPTION_VERTEX_INSET_M = 5


class NetRIDDisplayProviderUser(VirtualUser):
    """Virtual NetRID Display Provider serving virtual observers."""

    dss_instances: list[DSSInstance]
    dss_selection_strategy: ASTMDSSSelectionStrategy

    observer_behaviors: list[NetRIDObserverBehaviorSpecification]
    """Behavior of each virtual observer served by this display provider."""

    s2_grid: S2GriddedSubscriptionStrategySpecification

    random: Random

    subscriptions: dict[s2sphere.CellId, Subscription]
    """Subscription most recently established for each S2 cell, possibly expired."""

    last_queried: dict[s2sphere.CellId, datetime]
    """Time at which an observer query most recently covered each S2 cell."""

    pending_deletion_checks: set[s2sphere.CellId]
    """S2 cells for which a check for an unused subscription is already scheduled."""

    def __init__(
        self,
        user_id: str,
        user_spec: BenchmarkUserSpecification,
        resource_pool: dict[ResourceID, Any],
        executor: ThreadPoolExecutor,
        coordinator: Coordinator,
        record_operation: Callable[[ExecutedOperation], None],
        random: Random,
    ):
        super().__init__(
            user_id, user_spec.name, executor, coordinator, record_operation
        )
        if not user_spec.netrid_dp:
            raise ValueError(
                f"User specification '{user_spec.name}' has no netrid_dp definition"
            )
        spec = user_spec.netrid_dp

        self.dss_instances = []
        for res_id in spec.dss_pool:
            if res_id not in resource_pool:
                raise ValueError(
                    f"Resource '{res_id}' in netrid_dp.dss_pool not found in resource pool"
                )
            res = resource_pool[res_id]
            if isinstance(res, DSSInstancesResource):
                self.dss_instances.extend(res.dss_instances)
            elif isinstance(res, DSSInstanceResource):
                self.dss_instances.append(res.dss_instance)
            else:
                raise ValueError(
                    f"Resource '{res_id}' is not a uss_qualifier.resources.astm.f3411.dss.DSSInstanceResource nor uss_qualifier.resources.astm.f3411.dss.DSSInstancesResource"
                )

        if not self.dss_instances:
            raise ValueError(
                f"No NetRID DSS instances resolved from netrid_dp.dss_pool for user '{user_id}'"
            )

        if len(self.dss_instances) > 1:
            if spec.dss_selection_strategy:
                self.dss_selection_strategy = spec.dss_selection_strategy
            else:
                raise ValueError(
                    f"User `{user_id}` specified {len(self.dss_instances)} DSS instances but no dss_selection strategy"
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

        self.observer_behaviors = [
            observers.behavior
            for observers in spec.observers
            for _ in range(observers.count)
        ]

        if spec.subscription_strategy.s2_grid:
            self.s2_grid = spec.subscription_strategy.s2_grid
        else:
            raise NotImplementedError(
                f"No supported subscription strategy was specified in user `{user_id}` specification for netrid_dp.subscription_strategy"
            )

        self.random = random
        self.subscriptions = {}
        self.last_queried = {}
        self.pending_deletion_checks = set()

    def select_dss_instance(self) -> DSSInstance:
        if self.dss_selection_strategy == ASTMDSSSelectionStrategy.First:
            return self.dss_instances[0]
        elif self.dss_selection_strategy == ASTMDSSSelectionStrategy.Random:
            return self.random.choice(self.dss_instances)
        else:
            raise NotImplementedError(
                f"Unsupported DSS selection strategy `{self.dss_selection_strategy}`"
            )

    def _time_until_next_observation_period(
        self, behavior: NetRIDObserverBehaviorSpecification
    ) -> timedelta:
        mean_s = (
            behavior.mean_time_between_observation_periods.timedelta.total_seconds()
        )
        return timedelta(seconds=self.random.expovariate(1 / mean_s))

    async def start_observation_period(
        self, behavior: NetRIDObserverBehaviorSpecification
    ) -> list[Action]:
        t0 = datetime.now(UTC)
        lat = self.random.uniform(behavior.area.lat_min, behavior.area.lat_max)
        lng = self.random.uniform(behavior.area.lng_min, behavior.area.lng_max)
        view = s2sphere.LatLngRect.from_point_pair(
            s2sphere.LatLng.from_degrees(
                lat - behavior.view_lat_size / 2, lng - behavior.view_lng_size / 2
            ),
            s2sphere.LatLng.from_degrees(
                lat + behavior.view_lat_size / 2, lng + behavior.view_lng_size / 2
            ),
        )
        t_end = t0 + timedelta(
            seconds=self.random.uniform(
                behavior.min_observation_period_duration.timedelta.total_seconds(),
                behavior.max_observation_period_duration.timedelta.total_seconds(),
            )
        )

        return [
            Action(
                timestamp=t0,
                start=partial(self.observer_query, behavior, view, t0, t_end),
                run_on_shutdown=False,
            ),
            Action(
                timestamp=t_end + self._time_until_next_observation_period(behavior),
                start=partial(self.start_observation_period, behavior),
                run_on_shutdown=False,
            ),
        ]

    async def observer_query(
        self,
        behavior: NetRIDObserverBehaviorSpecification,
        view: s2sphere.LatLngRect,
        t_prev: datetime,
        t_end: datetime,
    ) -> list[Action]:
        if datetime.now(UTC) > t_end:
            return []

        new_actions: list[Action] = []

        coverer = s2sphere.RegionCoverer()
        coverer.min_level = self.s2_grid.s2_level
        coverer.max_level = self.s2_grid.s2_level
        # TODO: Serve cells in parallel
        for cell_id in coverer.get_covering(view):
            new_actions.extend(await self._serve_cell(cell_id))

        t_next = t_prev + behavior.query_interval.timedelta
        if t_next < t_end:
            new_actions.append(
                Action(
                    timestamp=t_next,
                    start=partial(self.observer_query, behavior, view, t_next, t_end),
                    run_on_shutdown=False,
                )
            )
        return new_actions

    async def _serve_cell(self, cell_id: s2sphere.CellId) -> list[Action]:
        now = datetime.now(UTC)
        self.last_queried[cell_id] = now

        subscription = self.subscriptions.get(cell_id, None)
        if not subscription or subscription.time_end <= now:
            await self._put_subscription(
                cell_id,
                str(uuid.uuid4()),
                now,
                now + self.s2_grid.initial_duration.timedelta,
                None,
            )
        elif subscription.time_end - now < self.s2_grid.extension_window.timedelta:
            await self._put_subscription(
                cell_id,
                subscription.id,
                None,
                subscription.time_end + self.s2_grid.extension_duration.timedelta,
                subscription.version,
            )

        if (
            self.s2_grid.delete_after_unused
            and cell_id in self.subscriptions
            and cell_id not in self.pending_deletion_checks
        ):
            self.pending_deletion_checks.add(cell_id)
            return [
                Action(
                    timestamp=now + self.s2_grid.delete_after_unused.timedelta,
                    start=partial(self.check_unused_subscription, cell_id),
                    run_on_shutdown=False,
                )
            ]
        return []

    async def _put_subscription(
        self,
        cell_id: s2sphere.CellId,
        subscription_id: str,
        start_time: datetime | None,
        end_time: datetime,
        subscription_version: str | None,
    ) -> None:
        dss_instance = self.select_dss_instance()
        cell = s2sphere.Cell(cell_id)
        center = cell.get_center()
        area_vertices = []
        for v in range(4):
            vertex = cell.get_vertex(v)
            f = SUBSCRIPTION_VERTEX_INSET_M / (vertex.angle(center) * EARTH_RADIUS_M)
            area_vertices.append(
                s2sphere.LatLng.from_point((vertex + (center - vertex) * f).normalize())
            )
        change = await self.run_sync_client_call(
            upsert_subscription,
            area_vertices=area_vertices,
            alt_lo=self.s2_grid.min_alt.to_w84_m(),
            alt_hi=self.s2_grid.max_alt.to_w84_m(),
            start_time=start_time,
            end_time=end_time,
            uss_base_url=make_fake_url(),
            subscription_id=subscription_id,
            rid_version=dss_instance.rid_version,
            utm_client=dss_instance.client,
            subscription_version=subscription_version,
            participant_id=dss_instance.participant_id,
        )
        self.record_query(change.query, successful=change.success)
        if change.subscription:
            self.subscriptions[cell_id] = change.subscription

    async def check_unused_subscription(self, cell_id: s2sphere.CellId) -> list[Action]:
        assert self.s2_grid.delete_after_unused  # Only scheduled in this case

        t_unused = (
            self.last_queried[cell_id] + self.s2_grid.delete_after_unused.timedelta
        )
        if t_unused > datetime.now(UTC):
            return [
                Action(
                    timestamp=t_unused,
                    start=partial(self.check_unused_subscription, cell_id),
                    run_on_shutdown=False,
                )
            ]

        self.pending_deletion_checks.discard(cell_id)
        await self._delete_subscription(cell_id)
        return []

    async def _delete_subscription(self, cell_id: s2sphere.CellId) -> None:
        subscription = self.subscriptions.pop(cell_id, None)
        if not subscription or subscription.time_end <= datetime.now(UTC):
            return

        dss_instance = self.select_dss_instance()
        change = await self.run_sync_client_call(
            delete_subscription,
            subscription_id=subscription.id,
            subscription_version=subscription.version,
            rid_version=dss_instance.rid_version,
            utm_client=dss_instance.client,
            participant_id=dss_instance.participant_id,
        )
        self.record_query(change.query, successful=change.success)
        if not change.success:
            self.subscriptions[cell_id] = subscription

    async def run_custom_workflow(self, stop_event: asyncio.Event) -> None:
        now = datetime.now(UTC)
        action_queue: list[Action] = [
            Action(
                timestamp=now + self._time_until_next_observation_period(behavior),
                start=partial(self.start_observation_period, behavior),
                run_on_shutdown=False,
            )
            for behavior in self.observer_behaviors
        ]
        heapq.heapify(action_queue)

        while action_queue and not stop_event.is_set():
            next_action = heapq.heappop(action_queue)

            dt = next_action.timestamp - datetime.now(UTC)
            if dt.total_seconds() > 0:
                await self.sleep_interruptible(dt.total_seconds(), stop_event)
                if stop_event.is_set():
                    break

            for action in await next_action.start():
                heapq.heappush(action_queue, action)

    async def cleanup(self) -> None:
        for cell_id in list(self.subscriptions):
            await self._delete_subscription(cell_id)

        if self.subscriptions:
            logger.warning(
                f"{self.user_id} was unable to clean up {len(self.subscriptions)} RID subscriptions"
            )
