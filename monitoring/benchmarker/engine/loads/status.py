from datetime import datetime

from monitoring.benchmarker.configurations.loads import (
    OperationType,
    StepCompletionCriteria,
)
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.reports.report import BenchmarkScenarioStepReport


def throughput_of_step_ops(
    step: BenchmarkScenarioStepReport,
    operations: list[ExecutedOperation],
    op_types: set[str] | set[OperationType],
) -> float:
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
