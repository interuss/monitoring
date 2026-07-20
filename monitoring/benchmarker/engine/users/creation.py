from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from random import Random
from typing import Any

from monitoring.benchmarker.configurations.users import (
    BenchmarkUserSpecification,
)
from monitoring.benchmarker.engine.coordination import CoordinationGroupID, Coordinator
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
    coordinator: Coordinator,
    record_operation: Callable[[ExecutedOperation], None],
    random: Random,
) -> VirtualUser:
    if "flight_planner" in user_spec and user_spec.flight_planner is not None:
        return FlightPlannerUser(
            user_id,
            user_spec,
            resource_pool,
            executor,
            coordinator,
            record_operation,
            random,
        )
    else:
        raise NotImplementedError(
            f"User type '{user_spec.name}' does not specify any implemented behavior"
        )


def enumerate_coordination_groups(
    users: Sequence[BenchmarkUserSpecification],
) -> Iterable[CoordinationGroupID]:
    for user in users:
        if "flight_planner" in user and user.flight_planner:
            yield from FlightPlannerUser.enumerate_coordination_groups(
                user.flight_planner
            )
        else:
            raise NotImplementedError()
