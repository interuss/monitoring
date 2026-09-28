import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from random import Random
from typing import Any

from loguru import logger

from monitoring.benchmarker.configurations.loads import UserRampLoad
from monitoring.benchmarker.configurations.scenarios import BenchmarkScenarioName
from monitoring.benchmarker.configurations.users import (
    BenchmarkUserName,
    BenchmarkUserSpecification,
)
from monitoring.benchmarker.engine.coordination import Coordinator
from monitoring.benchmarker.engine.loads.criteria import check_load_completion_criteria
from monitoring.benchmarker.engine.loads.step_execution import (
    ActiveUser,
    StepProgressState,
    resolve_user_types,
    run_load_step,
    spawn_users_to_target,
    start_periodic_status_logger,
    wind_down_and_cleanup_remaining_users,
)
from monitoring.benchmarker.engine.operations import ExecutedOperation, record_operation
from monitoring.benchmarker.reports.report import (
    BenchmarkScenarioStepReport,
    CleanupReport,
    StepTerminationReason,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID


async def run_user_ramp_load(
    ramp: UserRampLoad,
    user_specs_map: dict[BenchmarkUserName, BenchmarkUserSpecification],
    resource_pool: dict[ResourceID, Any],
    executor: ThreadPoolExecutor,
    coordinator: Coordinator,
    scenario_name: BenchmarkScenarioName,
) -> tuple[list[ExecutedOperation], list[BenchmarkScenarioStepReport], CleanupReport]:
    """Apply a load by driving virtual user workflows and monitoring step criteria."""
    user_types_list = resolve_user_types(ramp, user_specs_map)
    random = (
        Random(ramp.random_seed)
        if "random_seed" in ramp and ramp.random_seed
        else Random()
    )

    active_users: list[ActiveUser] = []
    load_stop_event = asyncio.Event()

    operations: list[ExecutedOperation] = []
    steps: list[BenchmarkScenarioStepReport] = []

    current_load_factor = ramp.initial_users
    progress = StepProgressState()

    def wrapped_record_op(op: ExecutedOperation) -> None:
        if not op.successful:
            progress.update_status_time()
        record_operation(op, operations)

    logger.info(f"Starting user_ramp load with initial_users={current_load_factor}")
    progress.update_status_time()

    periodic_summary_task = start_periodic_status_logger(
        ramp, progress, operations, active_users, load_stop_event
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
                load=ramp,
                load_label="User ramp",
                scenario_name=scenario_name,
                current_load_factor=current_load_factor,
                progress=progress,
                active_users=active_users,
                operations=operations,
                load_stop_event=load_stop_event,
            )
            steps.append(step_report)

            if step_report.termination_reason != StepTerminationReason.Completed:
                logger.info(
                    f"Step {progress.step_index} terminated with reason '{step_report.termination_reason}'. Stopping load."
                )
                progress.update_status_time()
                load_stop_event.set()
                break

            if load_stop_event.is_set():
                break

            if check_load_completion_criteria(
                ramp.load_completion_criteria, steps, operations
            ):
                logger.info(
                    f"Load completion criteria met after step {progress.step_index}. Stopping load."
                )
                progress.update_status_time()
                load_stop_event.set()
                break

            progress.step_index += 1
            current_load_factor += ramp.additional_users_per_step
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
