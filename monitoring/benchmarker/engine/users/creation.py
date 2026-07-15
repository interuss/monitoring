from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from monitoring.benchmarker.configurations.users import (
    BenchmarkUserSpecification,
)
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.engine.users.flight_planner.flight_planner import (
    FlightPlannerUser,
)
from monitoring.benchmarker.engine.users.framework import VirtualUser
from monitoring.uss_qualifier.resources.definitions import ResourceID


def create_virtual_user(
    user_id: str,
    user_spec: BenchmarkUserSpecification,
    resource_pool: dict[ResourceID, Any],
    executor: ThreadPoolExecutor,
    record_operation: Callable[[ExecutedOperation], None],
) -> VirtualUser:
    if "flight_planner" in user_spec and user_spec.flight_planner is not None:
        return FlightPlannerUser(
            user_id, user_spec, resource_pool, executor, record_operation
        )
    else:
        raise NotImplementedError(
            f"User type '{user_spec.name}' does not specify any implemented behavior"
        )
