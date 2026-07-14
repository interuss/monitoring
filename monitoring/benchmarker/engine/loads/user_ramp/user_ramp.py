import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from implicitdict import StringBasedDateTime
from loguru import logger

from monitoring.benchmarker.configurations.loads import (
    UserRampLoad,
)
from monitoring.benchmarker.configurations.users import (
    BenchmarkUserName,
    BenchmarkUserSpecification,
)
from monitoring.benchmarker.engine.loads.criteria import (
    check_load_completion_criteria,
    check_stability_criteria,
    check_step_completion_criteria,
)
from monitoring.benchmarker.engine.loads.status import get_operations_of_interest
from monitoring.benchmarker.engine.loads.user_ramp.status import format_waiting_status
from monitoring.benchmarker.engine.operations import ExecutedOperation, record_operation
from monitoring.benchmarker.engine.users.creation import create_virtual_user
from monitoring.benchmarker.engine.users.framework import VirtualUser
from monitoring.benchmarker.reports.report import BenchmarkScenarioStepReport
from monitoring.uss_qualifier.resources.definitions import ResourceID

PERIODIC_STATUS_PERIOD_S = 30.0


async def run_user_ramp_load(
    ramp: UserRampLoad,
    user_specs_map: dict[BenchmarkUserName, BenchmarkUserSpecification],
    resource_pool: dict[ResourceID, Any],
    executor: ThreadPoolExecutor,
) -> tuple[list[ExecutedOperation], list[BenchmarkScenarioStepReport]]:
    """Apply a load by driving virtual user workflows and monitoring step criteria."""
    ramp_user_type = ramp.user_type
    if ramp_user_type not in user_specs_map:
        raise ValueError(
            f"User type '{ramp_user_type}' for UserRampLoad.user_type not found in configuration.user_types"
        )
    user_spec = user_specs_map[ramp_user_type]

    active_tasks: list[asyncio.Task] = []
    virtual_users: list[VirtualUser] = []
    stop_event = asyncio.Event()

    operations: list[ExecutedOperation] = []
    steps: list[BenchmarkScenarioStepReport] = []

    current_load_factor = ramp.initial_users
    step_index = 0
    step_start_time: datetime | None = None
    stability_time: datetime | None = None

    last_status_time = [time.monotonic()]

    def update_status_time() -> None:
        last_status_time[0] = time.monotonic()

    def wrapped_record_op(op: ExecutedOperation) -> None:
        update_status_time()
        record_operation(op, operations)

    logger.info(f"Starting user_ramp load with initial_users={current_load_factor}")
    update_status_time()

    # Print status periodically if no other status updates have happened recently
    async def _periodic_summary_logger() -> None:
        while not stop_event.is_set():
            now_t = time.monotonic()
            dt_s = last_status_time[0] + PERIODIC_STATUS_PERIOD_S - now_t
            if dt_s > 0:
                await asyncio.sleep(dt_s)
            elif not stop_event.is_set():
                last_status_time[0] = time.monotonic()
                msg = format_waiting_status(
                    ramp,
                    step_index,
                    operations,
                    step_start_time,
                    stability_time,
                    virtual_users,
                )
                logger.info(msg)

    periodic_summary_task = asyncio.create_task(_periodic_summary_logger())

    try:
        while not stop_event.is_set():
            # Start new step
            step_start_time = datetime.now(UTC)

            # Spawn new users for step
            first_user_spawned = None
            last_user_spawned = None
            while len(virtual_users) < current_load_factor:
                user_id = f"{user_spec.name}_{len(virtual_users) + 1}"
                if first_user_spawned is None:
                    first_user_spawned = user_id
                last_user_spawned = user_id
                vu = create_virtual_user(
                    user_id,
                    user_spec,
                    resource_pool,
                    executor,
                    wrapped_record_op,
                )
                virtual_users.append(vu)
                active_tasks.append(asyncio.create_task(vu.run_workflow(stop_event)))
            if first_user_spawned and last_user_spawned:
                logger.info(
                    f"Spawned virtual users '{first_user_spawned}' to '{last_user_spawned}'"
                )
                update_status_time()

            # Wait for throughput to become stable for this step
            stability_time = None
            while not stop_event.is_set():
                if check_stability_criteria(
                    ramp.throughput_stability_criteria,
                    operations,
                    virtual_users,
                    step_start_time,
                ):
                    stability_time = datetime.now(UTC)
                    logger.info(
                        f"Step {step_index} reached throughput stability after {(stability_time - step_start_time).total_seconds():.1f}s"
                    )
                    update_status_time()
                    break
                await asyncio.sleep(0.5)

            if stop_event.is_set() or stability_time is None:
                break

            step_end_time = datetime.now(UTC)

            # Wait for step to complete
            while not stop_event.is_set():
                now = datetime.now(UTC)
                if check_step_completion_criteria(
                    ramp.step_completion_criteria,
                    step_start_time,
                    stability_time,
                    now,
                    operations,
                ):
                    step_end_time = now
                    break
                await asyncio.sleep(0.5)

            # Summarize activity during step
            step_ops = [
                op
                for op in operations
                if op.completed_at.datetime >= step_start_time
                and op.completed_at.datetime <= step_end_time
            ]
            ops_of_interest = get_operations_of_interest(
                ramp.step_completion_criteria, step_ops, True
            )
            throughput_duration_s = (
                (step_end_time - stability_time).total_seconds()
                if stability_time
                else 0.0
            )
            step_duration_s = (step_end_time - step_start_time).total_seconds()

            valid_count = sum(
                1
                for op in step_ops
                if op.completed_at.datetime >= stability_time
                and op.type in ops_of_interest
                and op.successful
            )
            tp_valid = (
                valid_count / throughput_duration_s
                if throughput_duration_s > 0
                else 0.0
            )

            step_count = sum(
                1 for op in step_ops if op.type in ops_of_interest and op.successful
            )

            fails_by_type: dict[str, int] = {}
            for op in step_ops:
                if not op.successful:
                    t_str = str(op.type)
                    fails_by_type[t_str] = fails_by_type.get(t_str, 0) + 1

            failures_str = (
                ", ".join(f"{k}: {v}" for k, v in sorted(fails_by_type.items()))
                if fails_by_type
                else "0 failures"
            )
            ops_interest_str = (
                ", ".join(sorted(ops_of_interest))
                if ops_of_interest
                else "all operations"
            )

            logger.info(
                f"Step {step_index} completed (load_factor={current_load_factor}, operations of interest: [{ops_interest_str}]):\n"
                f"  • Validity Period Throughput: {tp_valid:.2f} ops/s across validity duration ({throughput_duration_s:.1f}s)\n"
                f"  • Operations of Interest Completed: {valid_count} in validity period ({throughput_duration_s:.1f}s), {step_count} started since step began; full step duration ({step_duration_s:.1f}s)\n"
                f"  • Failures during step: {failures_str}"
            )
            update_status_time()

            if stop_event.is_set():
                break

            # Report step
            step_report = BenchmarkScenarioStepReport(
                load_factor=float(current_load_factor),
                start_time=StringBasedDateTime(step_start_time),
                throughput_stability_time=StringBasedDateTime(stability_time),
                end_time=StringBasedDateTime(step_end_time),
            )
            steps.append(step_report)

            # Check if load is complete
            if check_load_completion_criteria(
                ramp.load_completion_criteria, steps, operations
            ):
                logger.info(
                    f"Load completion criteria met after step {step_index}. Stopping load."
                )
                update_status_time()
                stop_event.set()
                break

            # Move to next step
            step_index += 1
            current_load_factor += ramp.additional_users_per_step
            logger.info(
                f"Advancing to step {step_index} with load_factor={current_load_factor}"
            )
            update_status_time()
    finally:
        periodic_summary_task.cancel()
        if not stop_event.is_set():
            stop_event.set()
        logger.info(
            f"Waiting for {len(active_tasks)} active virtual users to wind down gracefully..."
        )
        await asyncio.gather(*active_tasks, return_exceptions=True)
        logger.info("All virtual users have finished.")

    return operations, steps
