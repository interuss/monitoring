import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from monitoring.benchmarker.configurations.users import (
    BenchmarkUserName,
)
from monitoring.benchmarker.engine.operations import ExecutedOperation


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

    @abstractmethod
    async def run_workflow(self, stop_event: asyncio.Event) -> None:
        raise NotImplementedError()
