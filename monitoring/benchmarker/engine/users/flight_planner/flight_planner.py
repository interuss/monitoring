import asyncio
import heapq
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from implicitdict import StringBasedDateTime
from loguru import logger

from monitoring.benchmarker.configurations.loads import OperationType, WorkflowType
from monitoring.benchmarker.configurations.users import (
    BenchmarkUserSpecification,
)
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.engine.users.flight_planner.astm_net_rid import (
    ASTMNetRIDHandler,
)
from monitoring.benchmarker.engine.users.flight_planner.flight_generation import (
    FlightGenerator,
    make_flight_generator,
)
from monitoring.benchmarker.engine.users.flight_planner.framework import (
    Flight,
    FlightAction,
    FlightID,
)
from monitoring.benchmarker.engine.users.framework import VirtualUser
from monitoring.uss_qualifier.resources.definitions import ResourceID


class FlightPlannerUser(VirtualUser):
    """Virtual user performing flight planning."""

    flight_generator: FlightGenerator
    """Means by which this user generates flights."""

    net_rid: ASTMNetRIDHandler | None = None
    """Means by which this user performs ASTM network remote ID (if any)."""

    flights: dict[FlightID, Flight]
    """Flights originating from this user with outstanding actions."""

    most_recent_flight: Flight | None = None
    """Most recent flight created by this user."""

    def __init__(
        self,
        user_id: str,
        user_spec: BenchmarkUserSpecification,
        resource_pool: dict[ResourceID, Any],
        executor: ThreadPoolExecutor,
        record_operation: Callable[[ExecutedOperation], None],
    ):
        super().__init__(user_id, user_spec.name, executor, record_operation)
        if "flight_planner" not in user_spec or not user_spec.flight_planner:
            raise ValueError(
                f"User specification '{user_spec.name}' has no flight_planner definition"
            )

        self.flight_generator = make_flight_generator(
            user_spec.flight_planner.flight_generation, user_id
        )

        if (
            "astm_netrid_behavior" in user_spec.flight_planner
            and user_spec.flight_planner.astm_netrid_behavior
        ):
            self.net_rid = ASTMNetRIDHandler(
                user_spec.flight_planner.astm_netrid_behavior, resource_pool, self
            )

        self.flights = {}

    async def _make_next_flight(self) -> list[FlightAction]:
        if not self.most_recent_flight:
            t_prev_flight = datetime.now(UTC)
        else:
            t_prev_flight = self.most_recent_flight.end_time

        flight = self.flight_generator.generate_flight(t_prev_flight)

        new_actions: list[FlightAction] = [
            FlightAction(
                timestamp=flight.end_time,
                flight_id=flight.id,
                start=flight.complete,
                run_on_shutdown=False,
            ),
            FlightAction(
                timestamp=flight.end_time,
                start=self._make_next_flight,
                run_on_shutdown=False,
            ),
        ]

        if self.net_rid:
            new_actions.extend(self.net_rid.get_utm_actions(flight))

        self.flights[flight.id] = flight
        self.most_recent_flight = flight

        return new_actions

    async def run_custom_workflow(self, stop_event: asyncio.Event) -> None:
        action_queue: list[FlightAction] = [
            FlightAction(
                timestamp=datetime.now(UTC),
                start=self._make_next_flight,
                run_on_shutdown=False,
            )
        ]

        while action_queue and not stop_event.is_set():
            # Grab the next-soonest action from the queue
            next_action = heapq.heappop(action_queue)

            # If the action is scheduled for the future, wait until then
            dt = next_action.timestamp - datetime.now(UTC)
            if dt.total_seconds() > 0:
                await self.sleep_interruptible(dt.total_seconds(), stop_event)
                if stop_event.is_set():
                    heapq.heappush(action_queue, next_action)
                    break

            # Perform the action
            new_actions = await next_action.start()
            t_action_complete = datetime.now(UTC)

            # Queue up any follow-up actions
            for action in new_actions:
                heapq.heappush(action_queue, action)

            if next_action.flight_id and not any(
                action.flight_id == next_action.flight_id for action in action_queue
            ):
                # This was the last action for this flight
                flight = self.flights.pop(next_action.flight_id)
                flight_op = ExecutedOperation(
                    type=OperationType(WorkflowType.FlightPlannerFlight),
                    origin=self.user_id,
                    initiated_at=StringBasedDateTime(
                        flight.earliest_action_initiated_at or flight.start_time
                    ),
                    completed_at=StringBasedDateTime(t_action_complete),
                    successful=flight.successful,
                    query=None,
                )
                self.record_operation(flight_op)

        if not stop_event.is_set():
            if not action_queue:
                reason = "no more actions were queued"
            else:
                reason = "of an unknown reason"
            logger.warning(
                f"Flight planner user {self.user_id} stopped early because {reason}"
            )

        # Run any outstanding actions that should run on shutdown
        while action_queue:
            next_action = heapq.heappop(action_queue)
            if next_action.run_on_shutdown:
                await next_action.start()
