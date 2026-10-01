import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from random import Random
from typing import Any

from loguru import logger

from monitoring.benchmarker.configurations.loads import UserSearchLoad
from monitoring.benchmarker.configurations.scenarios import BenchmarkScenarioName
from monitoring.benchmarker.configurations.users import (
    BenchmarkUserName,
    BenchmarkUserSpecification,
)
from monitoring.benchmarker.engine.coordination import Coordinator
from monitoring.benchmarker.engine.loads.step_execution import (
    ActiveUser,
    StepProgressState,
    resolve_user_types,
    run_load_step,
    spawn_users_to_target,
    start_periodic_status_logger,
    stop_and_cleanup_users,
    wind_down_and_cleanup_remaining_users,
)
from monitoring.benchmarker.engine.loads.user_search.search import (
    determine_next_user_count,
)
from monitoring.benchmarker.engine.operations import ExecutedOperation, record_operation
from monitoring.benchmarker.reports.report import (
    BenchmarkScenarioStepReport,
    CleanupReport,
    StepTerminationReason,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID


async def run_user_search_load(
    search: UserSearchLoad,
    user_specs_map: dict[BenchmarkUserName, BenchmarkUserSpecification],
    resource_pool: dict[ResourceID, Any],
    executor: ThreadPoolExecutor,
    coordinator: Coordinator,
    scenario_name: BenchmarkScenarioName,
) -> tuple[list[ExecutedOperation], list[BenchmarkScenarioStepReport], CleanupReport]:
    """Apply a load by adaptively searching virtual user counts and monitoring step and search criteria."""
    user_types_list = resolve_user_types(search, user_specs_map)
    random = (
        Random(search.random_seed)
        if "random_seed" in search and search.random_seed
        else Random()
    )

    active_users: list[ActiveUser] = []
    load_stop_event = asyncio.Event()

    operations: list[ExecutedOperation] = []
    steps: list[BenchmarkScenarioStepReport] = []

    initial_next = determine_next_user_count(search, steps, operations)
    if initial_next is None:
        raise ValueError("Search completion criteria already satisfied before any step")
    current_load_factor = initial_next
    progress = StepProgressState()

    def wrapped_record_op(op: ExecutedOperation) -> None:
        if not op.successful:
            progress.update_status_time()
        record_operation(op, operations)

    logger.info(f"Starting user_search load with initial_users={current_load_factor}")
    progress.update_status_time()

    periodic_summary_task = start_periodic_status_logger(
        search, progress, operations, active_users, load_stop_event
    )

    try:
        while not load_stop_event.is_set():
            progress.step_start_time = datetime.now(UTC)

            spawn_users_to_target(
                target_load_factor=current_load_factor,
                active_users=active_users,
                user_types_list=user_types_list,
                user_specs_map=user_specs_map,
                resource_pool=resource_pool,
                executor=executor,
                coordinator=coordinator,
                record_op=wrapped_record_op,
                random=random,
            )
            progress.update_status_time()

            step_report = await run_load_step(
                load=search,
                load_label="User search",
                scenario_name=scenario_name,
                current_load_factor=current_load_factor,
                progress=progress,
                active_users=active_users,
                operations=operations,
                load_stop_event=load_stop_event,
            )
            steps.append(step_report)

            if load_stop_event.is_set():
                break

            # Recover from an unstable step by gracefully stopping and cleaning up all its users before proceeding
            if step_report.termination_reason != StepTerminationReason.Completed:
                await stop_and_cleanup_users(
                    active_users,
                    reason=f"recovering from unstable step {progress.step_index} ({step_report.termination_reason})",
                )
                active_users.clear()
                progress.update_status_time()

            # Determine next step user count or finish if search_completion_criteria are met
            next_load_factor = determine_next_user_count(search, steps, operations)
            if next_load_factor is None:
                logger.info(
                    f"Search completion criteria met after step {progress.step_index}. Stopping load."
                )
                progress.update_status_time()
                load_stop_event.set()
                break

            # If transitioning from a stable step to a lower user count, stop only the excess users
            if len(active_users) > next_load_factor:
                excess_users = active_users[next_load_factor:]
                del active_users[next_load_factor:]
                await stop_and_cleanup_users(
                    excess_users,
                    reason=f"reducing load factor from {current_load_factor} to {next_load_factor}",
                )
                progress.update_status_time()

            progress.step_index += 1
            current_load_factor = next_load_factor
            logger.info(
                f"Advancing to step {progress.step_index} for scenario '{scenario_name}' with load_factor={current_load_factor}"
            )
            progress.update_status_time()
    finally:
        periodic_summary_task.cancel()
        if not load_stop_event.is_set():
            load_stop_event.set()
        cleanup_report = await wind_down_and_cleanup_remaining_users(active_users)

    return operations, steps, cleanup_report
