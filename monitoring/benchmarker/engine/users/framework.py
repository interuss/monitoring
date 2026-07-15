import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Self

from implicitdict import StringBasedDateTime
from loguru import logger

from monitoring.benchmarker.configurations.loads import OperationType
from monitoring.benchmarker.configurations.users import (
    BenchmarkUserName,
)
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.monitorlib.fetch import Query


class VirtualUser(ABC):
    """Base class for virtual users generating load."""

    user_id: str
    """Identity of the user for origin identification, etc."""

    user_type_name: BenchmarkUserName

    executor: ThreadPoolExecutor
    """Means by which to perform synchronous work in the async context."""

    record_operation: Callable[[ExecutedOperation], None]
    """Means by which to record an operation completed by the virtual user."""

    def __init__(
        self,
        user_id: str,
        user_type_name: BenchmarkUserName,
        executor: ThreadPoolExecutor,
        record_operation: Callable[[ExecutedOperation], None],
    ):
        self.user_id = user_id
        self.user_type_name = user_type_name
        self.executor = executor
        self.record_operation = record_operation

    async def run_sync_client_call(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))

    async def sleep_interruptible(
        self, seconds: float, stop_event: asyncio.Event
    ) -> None:
        """Sleep in short intervals to wake up quickly if stop_event is set."""
        elapsed = 0.0
        while elapsed < seconds and not stop_event.is_set():
            slice_dur = min(0.1, seconds - elapsed)
            await asyncio.sleep(slice_dur)
            elapsed += slice_dur

    def record_query(self, query: Query, successful: bool | None = None) -> None:
        if query.query_type is None:
            raise NotImplementedError(
                f"Query type not specified for {query.request.method} query to {query.request.url}"
            )
        if successful is None:
            successful = query.status_code in (200, 201, 204)
        op = ExecutedOperation(
            type=OperationType(query.query_type),
            origin=self.user_id,
            initiated_at=StringBasedDateTime(query.request.timestamp),
            completed_at=StringBasedDateTime(query.response.reported.datetime),
            successful=successful,
            query=query,
        )
        self.record_operation(op)

    async def run_workflow(self, stop_event: asyncio.Event) -> None:
        try:
            await self.run_custom_workflow(stop_event)
        except Exception as e:
            logger.error(f"Error during user {self.user_id} workflow: {e}")
    
    @abstractmethod
    async def run_custom_workflow(self, stop_event: asyncio.Event) -> None:
        raise NotImplementedError()


@dataclass(order=True, kw_only=True)
class Action:
    timestamp: datetime
    start: Callable[[], Awaitable[list[Self]]] = field(compare=False)
    run_on_shutdown: bool
