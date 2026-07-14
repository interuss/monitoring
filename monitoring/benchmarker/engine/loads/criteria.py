from datetime import datetime

from monitoring.benchmarker.configurations.loads import (
    LoadCompletionCriteria,
    StepCompletionCriteria,
    ThroughputStabilityCriteria,
)
from monitoring.benchmarker.engine.loads.status import throughput_of_step_ops
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.engine.users.framework import VirtualUser
from monitoring.benchmarker.reports.report import BenchmarkScenarioStepReport


def check_stability_criteria(
    criteria: ThroughputStabilityCriteria,
    operations: list[ExecutedOperation],
    virtual_users: list[VirtualUser],
    step_start_time: datetime,
) -> bool:
    if (
        "each_user_completed_at_least" in criteria
        and criteria.each_user_completed_at_least
    ):
        req_count = criteria.each_user_completed_at_least.count
        req_ops = set(criteria.each_user_completed_at_least.operations)

        user_counts: dict[str, int] = {vu.user_id: 0 for vu in virtual_users}
        for op in operations:
            if op.initiated_at.datetime < step_start_time:
                continue
            if op.successful and str(op.type) in req_ops and op.origin in user_counts:
                user_counts[op.origin] += 1

        return all(c >= req_count for c in user_counts.values())
    else:
        raise NotImplementedError(
            "No supported criteria specified in ThroughputStabilityCriteria"
        )


def check_step_completion_criteria(
    criteria: StepCompletionCriteria,
    step_start_time: datetime,
    stability_time: datetime,
    now: datetime,
    operations: list[ExecutedOperation],
) -> bool:
    has_any_of = "any_of" in criteria and criteria.any_of
    has_duration = (
        "sampling_duration_at_least" in criteria and criteria.sampling_duration_at_least
    )
    has_completed_ops = "completed_at_least" in criteria and criteria.completed_at_least
    has_min_average = (
        "average_duration_more_than" in criteria and criteria.average_duration_more_than
    )
    has_stability_duration = (
        "throughput_stability_took_longer_than" in criteria
        and criteria.throughput_stability_took_longer_than
    )

    if (
        not has_any_of
        and not has_duration
        and not has_completed_ops
        and not has_min_average
        and not has_stability_duration
    ):
        raise NotImplementedError("StepCompletionCriteria has no specified conditions")

    if has_any_of and criteria.any_of:
        if not any(
            check_step_completion_criteria(
                child,
                step_start_time,
                stability_time,
                now,
                operations,
            )
            for child in criteria.any_of
        ):
            return False

    if has_duration and criteria.sampling_duration_at_least:
        required_duration = criteria.sampling_duration_at_least.timedelta
        if now - stability_time < required_duration:
            return False

    if has_completed_ops and criteria.completed_at_least:
        req_count = criteria.completed_at_least.count
        relevant_ops = set(criteria.completed_at_least.operations)
        completed = sum(
            1
            for op in operations
            if op.successful
            and op.completed_at.datetime >= stability_time
            and op.type in relevant_ops
            and op.completed_at.datetime <= now
        )
        if completed < req_count:
            return False

    if has_min_average and criteria.average_duration_more_than:
        required_duration_s = (
            criteria.average_duration_more_than.duration.timedelta.total_seconds()
        )
        relevant_ops = set(criteria.average_duration_more_than.operations)
        matching_ops = [
            op
            for op in operations
            if op.successful
            and op.completed_at.datetime >= stability_time
            and op.type in relevant_ops
            and stability_time <= op.completed_at.datetime <= now
        ]
        if not matching_ops:
            return False
        average_duration_s = sum(
            (op.completed_at.datetime - op.initiated_at.datetime).total_seconds()
            for op in matching_ops
        ) / len(matching_ops)
        if average_duration_s <= required_duration_s:
            return False

    if has_stability_duration and criteria.throughput_stability_took_longer_than:
        required_duration = criteria.throughput_stability_took_longer_than.timedelta
        if stability_time - step_start_time <= required_duration:
            return False

    return True


def check_load_completion_criteria(
    criteria: LoadCompletionCriteria,
    steps: list[BenchmarkScenarioStepReport],
    operations: list[ExecutedOperation],
) -> bool:
    has_any_of = "any_of" in criteria and criteria.any_of
    has_throughput = (
        "throughput_lower_than_peak" in criteria and criteria.throughput_lower_than_peak
    )
    has_failures = "failures_more_than" in criteria and criteria.failures_more_than
    has_most_recent_step = "most_recent_step" in criteria and criteria.most_recent_step

    if (
        not has_any_of
        and not has_throughput
        and not has_failures
        and not has_most_recent_step
    ):
        raise NotImplementedError(
            "LoadCompletionCriteria specified no supported conditions"
        )

    if has_any_of and criteria.any_of:
        if not any(
            check_load_completion_criteria(child, steps, operations)
            for child in criteria.any_of
        ):
            return False

    if has_throughput and criteria.throughput_lower_than_peak:
        if len(steps) < 2:
            return False
        op_types = set(criteria.throughput_lower_than_peak.operations)
        last_step_idx = len(steps) - 1
        last_tp = throughput_of_step_ops(steps[last_step_idx], operations, op_types)
        peak_tp = max(
            throughput_of_step_ops(steps[idx], operations, op_types)
            for idx in range(last_step_idx)
        )
        if last_tp >= peak_tp * criteria.throughput_lower_than_peak.fraction_of_peak:
            return False

    if has_failures and criteria.failures_more_than:
        req_count = criteria.failures_more_than.count
        op_types = set(criteria.failures_more_than.operations)
        fails = sum(1 for op in operations if not op.successful and op.type in op_types)
        if fails <= req_count:
            return False

    if has_most_recent_step and criteria.most_recent_step:
        if not steps:
            return False
        last_step = steps[-1]
        step_start_time = last_step.start_time.datetime
        stability_time = last_step.throughput_stability_time.datetime
        now = last_step.end_time.datetime
        if not check_step_completion_criteria(
            criteria.most_recent_step,
            step_start_time,
            stability_time,
            now,
            operations,
        ):
            return False

    return True
