import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from implicitdict import StringBasedDateTime

from monitoring.benchmarker.configurations.loads import OperationType, WorkflowType
from monitoring.benchmarker.configurations.users import (
    BenchmarkUserSpecification,
)
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.engine.users.framework import VirtualUser
from monitoring.uss_qualifier.resources.definitions import ResourceID


class FlightPlannerUser(VirtualUser):
    """Virtual user performing flight planning."""

    def __init__(
        self,
        user_id: str,
        user_spec: BenchmarkUserSpecification,
        resource_pool: dict[ResourceID, Any],
        executor: ThreadPoolExecutor,
        record_operation: Callable[[ExecutedOperation], None],
    ):
        super().__init__(user_id, user_spec.name, executor, record_operation)

        self.record_operation = record_operation

        # TODO: Implement

    async def _sleep_interruptible(
        self, seconds: float, stop_event: asyncio.Event
    ) -> None:
        """Sleep in short intervals to wake up quickly if stop_event is set."""
        elapsed = 0.0
        while elapsed < seconds and not stop_event.is_set():
            slice_dur = min(0.5, seconds - elapsed)
            await asyncio.sleep(slice_dur)
            elapsed += slice_dur

    async def run_workflow(self, stop_event: asyncio.Event) -> None:
        duration_ms = 200
        duration_ms_dt = 200
        while not stop_event.is_set():
            t_start = datetime.now(UTC)

            # TODO: Perform real flight planning work
            await self._sleep_interruptible(duration_ms * 0.001, stop_event)
            duration_ms += duration_ms_dt

            t_end = datetime.now(UTC)

            flight_op = ExecutedOperation(
                type=OperationType(WorkflowType.FlightPlannerFlight),
                origin=self.user_id,
                initiated_at=StringBasedDateTime(t_start),
                completed_at=StringBasedDateTime(t_end),
                successful=True,
            )
            self.record_operation(flight_op)

            if stop_event.is_set():
                break
