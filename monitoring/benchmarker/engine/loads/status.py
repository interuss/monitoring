from datetime import UTC, datetime

from implicitdict import StringBasedDateTime
from loguru import logger

from monitoring.benchmarker.configurations.loads import (
    OperationType,
    StepCompletionCriteria,
    UserBasedLoad,
)
from monitoring.benchmarker.configurations.scenarios import BenchmarkScenarioName
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.engine.users.framework import VirtualUser
from monitoring.benchmarker.reports.report import (
    BenchmarkScenarioStepReport,
    StepTerminationReason,
)


def throughput_of_step_ops(
    step: BenchmarkScenarioStepReport,
    operations: list[ExecutedOperation],
    op_types: set[str] | set[OperationType],
) -> float:
    if not step.throughput_stability_time:
        return 0
    start_time = step.throughput_stability_time.datetime
    end_time = step.end_time.datetime
    count = sum(
        1
        for op in operations
        if op.successful
        and op.type in op_types
        and op.completed_at.datetime >= start_time
        and op.completed_at.datetime <= end_time
    )
    dur = (end_time - start_time).total_seconds()
    return count / dur if dur > 0 else 0.0


def format_step_completion_progress(
    criteria: StepCompletionCriteria,
    step_start_time: datetime,
    stability_time: datetime,
    now: datetime,
    operations: list[ExecutedOperation],
) -> list[str]:
    parts: list[str] = []
    if "sampling_duration_at_least" in criteria and criteria.sampling_duration_at_least:
        req_dur = criteria.sampling_duration_at_least.timedelta.total_seconds()
        cur_dur = (now - stability_time).total_seconds()
        parts.append(
            f"sampling_duration_at_least (threshold: {req_dur:.1f}s, current: {cur_dur:.1f}s)"
        )

    if "completed_at_least" in criteria and criteria.completed_at_least:
        req_count = criteria.completed_at_least.count
        req_ops = set(criteria.completed_at_least.operations)
        completed = sum(
            1
            for op in operations
            if op.successful
            and op.completed_at.datetime >= stability_time
            and op.type in req_ops
            and op.completed_at.datetime <= now
        )
        ops_str = ", ".join(sorted(req_ops))
        parts.append(
            f"completed_at_least (threshold: {req_count} of [{ops_str}], current: {completed})"
        )

    if "average_duration_more_than" in criteria and criteria.average_duration_more_than:
        req_dur = criteria.average_duration_more_than.duration.timedelta.total_seconds()
        req_ops = set(criteria.average_duration_more_than.operations)
        matching_ops = [
            op
            for op in operations
            if op.successful
            and op.completed_at.datetime >= step_start_time
            and op.type in req_ops
            and stability_time <= op.completed_at.datetime <= now
        ]
        if matching_ops:
            cur_dur = sum(
                (op.completed_at.datetime - op.initiated_at.datetime).total_seconds()
                for op in matching_ops
            ) / len(matching_ops)
            cur_str = f"{cur_dur:.1f}s"
        else:
            cur_str = "N/A"
        ops_str = ", ".join(sorted(req_ops))
        parts.append(
            f"average_duration_more_than (threshold: {req_dur:.1f}s of [{ops_str}], current: {cur_str})"
        )

    if (
        "throughput_stability_took_longer_than" in criteria
        and criteria.throughput_stability_took_longer_than
    ):
        req_dur = (
            criteria.throughput_stability_took_longer_than.timedelta.total_seconds()
        )
        cur_dur = (stability_time - step_start_time).total_seconds()
        parts.append(
            f"throughput_stability_took_longer_than (threshold: {req_dur:.1f}s, current: {cur_dur:.1f}s)"
        )

    if "any_of" in criteria and criteria.any_of is not None:
        child_parts = []
        for child in criteria.any_of:
            sub = format_step_completion_progress(
                child,
                step_start_time,
                stability_time,
                now,
                operations,
            )
            if sub:
                child_parts.append("(" + " AND ".join(sub) + ")")
        if child_parts:
            parts.append(" OR ".join(child_parts))
    return parts


def get_operations_of_interest(
    criteria: StepCompletionCriteria,
    all_step_ops: list[ExecutedOperation],
    with_defaults: bool = False,
) -> set[OperationType]:
    ops: set[OperationType] = set()
    if "completed_at_least" in criteria and criteria.completed_at_least:
        for o in criteria.completed_at_least.operations:
            ops.add(o)
    if "average_duration_more_than" in criteria and criteria.average_duration_more_than:
        for o in criteria.average_duration_more_than.operations:
            ops.add(o)
    if "any_of" in criteria and criteria.any_of is not None:
        for child in criteria.any_of:
            ops.update(get_operations_of_interest(child, all_step_ops))
    if not ops and with_defaults:
        ops = {op.type for op in all_step_ops}
    return ops


def format_waiting_status(
    load: UserBasedLoad,
    step_index: int,
    operations: list[ExecutedOperation],
    step_start_time: datetime | None,
    stability_time: datetime | None,
    virtual_users: list[VirtualUser],
) -> str:
    if step_start_time is None:
        return f"[Step {step_index} waiting to start]"

    if stability_time is None:
        if (
            "each_user_completed_at_least" in load.throughput_stability_criteria
            and load.throughput_stability_criteria.each_user_completed_at_least
        ):
            crit = load.throughput_stability_criteria.each_user_completed_at_least
            req_count = crit.count
            req_ops = set(crit.operations)
            user_counts: dict[str, int] = {vu.user_id: 0 for vu in virtual_users}
            for op in operations:
                if (
                    op.successful
                    and op.completed_at.datetime >= step_start_time
                    and op.type in req_ops
                    and op.origin in user_counts
                ):
                    user_counts[op.origin] += 1
            counts = list(user_counts.values())
            met_users = sum(1 for c in counts if c >= req_count)
            max_c = max(counts) if counts else 0
            min_c = min(counts) if counts else 0
            ops_str = ", ".join(sorted(req_ops))
            return f"[Step {step_index} waiting for throughput stability] each_user_completed_at_least (threshold: {req_count} of [{ops_str}]): {met_users}/{len(virtual_users)} users met threshold | most advanced user: {max_c} completed, least advanced user: {min_c} completed"
        else:
            return f"[Step {step_index} waiting for throughput stability] (evaluating stability criteria)"
    else:
        now = datetime.now(UTC)
        progress = (
            format_step_completion_progress(
                load.step_completion_criteria,
                step_start_time,
                stability_time,
                now,
                operations,
            )
            if step_start_time is not None
            else []
        )
        cond_str = (
            " AND ".join(progress)
            if progress
            else "(evaluating step completion criteria)"
        )
        return f"[Step {step_index} waiting for step completion] {cond_str}"


def summarize_and_report_step(
    load_label: str,
    scenario_name: BenchmarkScenarioName,
    step_index: int,
    load_factor: float,
    step_start_time: datetime,
    stability_time: datetime | None,
    step_end_time: datetime,
    is_unstable: bool,
    step_completion_criteria: StepCompletionCriteria,
    operations: list[ExecutedOperation],
    total_tasks: int,
    ended_tasks: int,
) -> BenchmarkScenarioStepReport:
    """Log a summary of step activity and return its BenchmarkScenarioStepReport."""
    step_ops = [
        op
        for op in operations
        if op.completed_at.datetime >= step_start_time
        and op.completed_at.datetime <= step_end_time
    ]
    ops_of_interest = get_operations_of_interest(
        step_completion_criteria, step_ops, True
    )
    throughput_duration_s = (
        (step_end_time - stability_time).total_seconds() if stability_time else 0.0
    )
    step_duration_s = (step_end_time - step_start_time).total_seconds()

    valid_count = (
        sum(
            1
            for op in step_ops
            if op.completed_at.datetime >= stability_time
            and op.type in ops_of_interest
            and op.successful
        )
        if stability_time
        else 0
    )
    tp_valid = valid_count / throughput_duration_s if throughput_duration_s > 0 else 0.0

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
        ", ".join(sorted(ops_of_interest)) if ops_of_interest else "all operations"
    )

    if stability_time is None:
        termination_reason = StepTerminationReason.StabilityNotAchieved
    elif is_unstable:
        termination_reason = StepTerminationReason.Unstable
    else:
        termination_reason = StepTerminationReason.Completed

    logger.info(
        f"{load_label} step {step_index} for scenario '{scenario_name}' ended with termination_reason='{termination_reason}' (load_factor={load_factor}, operations of interest: [{ops_interest_str}]):\n"
        f"  • Operations of Interest Completed: {valid_count} ({tp_valid:.2f} ops/s) in validity period ({throughput_duration_s:.1f}s), {step_count} started since step began; full step duration ({step_duration_s:.1f}s)\n"
        f"  • Failures during step: {failures_str}\n"
        f"  • Tasks: {total_tasks} total, {ended_tasks} ended"
    )

    return BenchmarkScenarioStepReport(
        load_factor=float(load_factor),
        start_time=StringBasedDateTime(step_start_time),
        throughput_stability_time=StringBasedDateTime(stability_time)
        if stability_time
        else None,
        end_time=StringBasedDateTime(step_end_time),
        termination_reason=termination_reason,
    )
