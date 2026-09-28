import asyncio
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from random import Random
from typing import Any

from implicitdict import StringBasedDateTime
from loguru import logger

from monitoring.benchmarker.configurations.loads import UserBasedLoad
from monitoring.benchmarker.configurations.scenarios import BenchmarkScenarioName
from monitoring.benchmarker.configurations.users import (
    BenchmarkUserName,
    BenchmarkUserSpecification,
)
from monitoring.benchmarker.engine.coordination import Coordinator
from monitoring.benchmarker.engine.loads.criteria import (
    check_stability_criteria,
    check_step_completion_criteria,
)
from monitoring.benchmarker.engine.loads.status import (
    format_waiting_status,
    summarize_and_report_step,
)
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.engine.users.creation import create_virtual_user
from monitoring.benchmarker.engine.users.framework import VirtualUser
from monitoring.benchmarker.reports.report import (
    BenchmarkScenarioStepReport,
    CleanupReport,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID

PERIODIC_STATUS_PERIOD_S = 30.0


@dataclass
class ActiveUser:
    user: VirtualUser
    stop_event: asyncio.Event
    task: asyncio.Task


@dataclass
class StepProgressState:
    step_index: int = 0
    step_start_time: datetime | None = None
    stability_time: datetime | None = None
    last_status_time: float = field(default_factory=time.monotonic)

    def update_status_time(self) -> None:
        self.last_status_time = time.monotonic()


def resolve_user_types(
    load: UserBasedLoad,
    user_specs_map: dict[BenchmarkUserName, BenchmarkUserSpecification],
) -> list[BenchmarkUserName]:
    """Validate and return the list of user type names configured on a load."""
    load_type_name = type(load).__name__
    if "user_types" in load and load.user_types:
        user_types_list = load.user_types
        for ut in user_types_list:
            if ut not in user_specs_map:
                raise ValueError(
                    f"User type '{ut}' for {load_type_name}.user_types not found in configuration.user_types"
                )
        return user_types_list
    elif "user_type" in load and load.user_type:
        if load.user_type not in user_specs_map:
            raise ValueError(
                f"User type '{load.user_type}' for {load_type_name}.user_type not found in configuration.user_types"
            )
        return [load.user_type]
    else:
        raise ValueError(
            f"Neither user_type nor user_types specified for {load_type_name}"
        )


def start_periodic_status_logger(
    load: UserBasedLoad,
    progress: StepProgressState,
    operations: list[ExecutedOperation],
    active_users: list[ActiveUser],
    load_stop_event: asyncio.Event,
) -> asyncio.Task:
    """Start background task that logs waiting status periodically when no recent updates occurred."""

    async def _periodic_summary_logger() -> None:
        while not load_stop_event.is_set():
            now_t = time.monotonic()
            dt_s = progress.last_status_time + PERIODIC_STATUS_PERIOD_S - now_t
            if dt_s > 0:
                await asyncio.sleep(dt_s)
            elif not load_stop_event.is_set():
                progress.update_status_time()
                msg = format_waiting_status(
                    load,
                    progress.step_index,
                    operations,
                    progress.step_start_time,
                    progress.stability_time,
                    [au.user for au in active_users],
                )
                logger.info(msg)

    return asyncio.create_task(_periodic_summary_logger())


def spawn_users_to_target(
    target_load_factor: int,
    active_users: list[ActiveUser],
    user_types_list: list[BenchmarkUserName],
    user_specs_map: dict[BenchmarkUserName, BenchmarkUserSpecification],
    resource_pool: dict[ResourceID, Any],
    executor: ThreadPoolExecutor,
    coordinator: Coordinator,
    record_op: Callable[[ExecutedOperation], None],
    random: Random,
) -> None:
    """Spawn additional virtual users until len(active_users) reaches target_load_factor."""
    first_user_spawned = None
    last_user_spawned = None
    while len(active_users) < target_load_factor:
        user_spec = user_specs_map[
            user_types_list[len(active_users) % len(user_types_list)]
        ]
        user_id = f"{user_spec.name}_{len(active_users) + 1}"
        if first_user_spawned is None:
            first_user_spawned = user_id
        last_user_spawned = user_id
        vu = create_virtual_user(
            user_id,
            user_spec,
            resource_pool,
            executor,
            coordinator,
            record_op,
            Random(random.randint(0, 1 << 30)),
        )
        user_stop = asyncio.Event()
        user_task = asyncio.create_task(vu.run_workflow(user_stop))
        active_users.append(ActiveUser(user=vu, stop_event=user_stop, task=user_task))

    if first_user_spawned and last_user_spawned:
        if first_user_spawned == last_user_spawned:
            logger.info(f"Spawned virtual user '{first_user_spawned}'")
        else:
            logger.info(
                f"Spawned virtual users '{first_user_spawned}' to '{last_user_spawned}'"
            )
    else:
        logger.info(f"Continuing with {len(active_users)} existing virtual users")


async def stop_and_cleanup_users(users: list[ActiveUser], reason: str) -> None:
    """Signal virtual users to stop, wait for their workflows to finish, and clean them up."""
    if not users:
        return
    logger.info(
        f"Stopping {len(users)} virtual users ({reason}) and waiting for workflows to wind down gracefully..."
    )
    for au in users:
        au.stop_event.set()
    await asyncio.gather(*(au.task for au in users), return_exceptions=True)
    for au in users:
        await au.user.cleanup()
    logger.info(f"Finished stopping and cleaning up {len(users)} virtual users.")


async def wind_down_and_cleanup_remaining_users(
    active_users: list[ActiveUser],
) -> CleanupReport:
    """Stop any remaining active virtual users at the end of a load and clean them up."""
    if active_users:
        for au in active_users:
            au.stop_event.set()
        logger.info(
            f"Waiting for {len(active_users)} active virtual users to wind down gracefully..."
        )
        await asyncio.gather(*(au.task for au in active_users), return_exceptions=True)
        logger.info("All virtual users have finished their workflows.")

    logger.info(f"Cleaning up {len(active_users)} virtual users...")
    cleanup_start = datetime.now(UTC)
    for au in active_users:
        await au.user.cleanup()
    active_users.clear()
    cleanup_end = datetime.now(UTC)
    logger.info("All virtual users have been cleaned up.")
    return CleanupReport(
        start_time=StringBasedDateTime(cleanup_start),
        end_time=StringBasedDateTime(cleanup_end),
    )


async def run_load_step(
    load: UserBasedLoad,
    load_label: str,
    scenario_name: BenchmarkScenarioName,
    current_load_factor: int,
    progress: StepProgressState,
    active_users: list[ActiveUser],
    operations: list[ExecutedOperation],
    load_stop_event: asyncio.Event,
) -> BenchmarkScenarioStepReport:
    """Monitor throughput stability, instability, and completion criteria for a single load step."""
    step_index = progress.step_index
    step_start_time = progress.step_start_time or datetime.now(UTC)
    progress.step_start_time = step_start_time
    progress.stability_time = None

    current_virtual_users = [au.user for au in active_users]

    # Wait for throughput to become stable for this step
    stability_time: datetime | None = None
    is_unstable = False
    step_end_time = datetime.now(UTC)
    while not load_stop_event.is_set():
        now = datetime.now(UTC)
        if (
            "throughput_instability_criteria" in load
            and load.throughput_instability_criteria
            and check_stability_criteria(
                load.throughput_instability_criteria,
                operations,
                current_virtual_users,
                step_start_time,
                now,
            )
        ):
            logger.warning(
                f"Step {step_index} (load_factor={current_load_factor}) became unstable during throughput stability phase after {(now - step_start_time).total_seconds():.1f}s"
            )
            is_unstable = True
            step_end_time = now
            break

        if check_stability_criteria(
            load.throughput_stability_criteria,
            operations,
            current_virtual_users,
            step_start_time,
            now,
        ):
            stability_time = now
            progress.stability_time = stability_time
            logger.info(
                f"Step {step_index} (load_factor={current_load_factor}) reached throughput stability after {(stability_time - step_start_time).total_seconds():.1f}s"
            )
            progress.update_status_time()
            break

        if active_users and all(au.task.done() for au in active_users):
            load_stop_event.set()
        await asyncio.sleep(0.5)

    if not load_stop_event.is_set() and stability_time is not None and not is_unstable:
        step_end_time = datetime.now(UTC)

        # Wait for step to complete
        while not load_stop_event.is_set():
            now = datetime.now(UTC)
            if (
                "throughput_instability_criteria" in load
                and load.throughput_instability_criteria
                and check_stability_criteria(
                    load.throughput_instability_criteria,
                    operations,
                    current_virtual_users,
                    stability_time,
                    now,
                )
            ):
                logger.warning(
                    f"Step {step_index} (load_factor={current_load_factor}) became unstable during sampling phase after {(now - stability_time).total_seconds():.1f}s"
                )
                is_unstable = True
                step_end_time = now
                break

            if check_step_completion_criteria(
                load.step_completion_criteria,
                step_start_time,
                stability_time,
                now,
                operations,
            ):
                step_end_time = now
                break

            if active_users and all(au.task.done() for au in active_users):
                load_stop_event.set()
            await asyncio.sleep(0.5)
    elif stability_time is None:
        step_end_time = datetime.now(UTC)

    step_report = summarize_and_report_step(
        load_label=load_label,
        scenario_name=scenario_name,
        step_index=step_index,
        load_factor=current_load_factor,
        step_start_time=step_start_time,
        stability_time=stability_time,
        step_end_time=step_end_time,
        is_unstable=is_unstable,
        step_completion_criteria=load.step_completion_criteria,
        operations=operations,
        total_tasks=len(active_users),
        ended_tasks=sum(1 if au.task.done() else 0 for au in active_users),
    )
    progress.update_status_time()
    return step_report
