from dataclasses import dataclass, field
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


@dataclass
class OpsCounter:
    next_index: int
    count: int = 0
    total_s: float = 0.0
    counts_by_key: dict[str, int] = field(default_factory=dict)


def _consume_new_ops(
    counters: dict[tuple, OpsCounter] | None,
    key: tuple,
    operations: list[ExecutedOperation],
    ops_start: int,
) -> tuple[OpsCounter, list[ExecutedOperation]]:
    if counters is None:
        counter = OpsCounter(next_index=ops_start)
    else:
        counter = counters.setdefault(key, OpsCounter(next_index=ops_start))
    new_ops = operations[counter.next_index :]
    counter.next_index = len(operations)
    return counter, new_ops


def check_stability_criteria(
    criteria: ThroughputStabilityCriteria,
    operations: list[ExecutedOperation],
    virtual_users: list[VirtualUser],
    phase_start_time: datetime,
    now: datetime,
    step_start_time: datetime,
    counters: dict[tuple, OpsCounter] | None = None,
    phase_ops_start: int = 0,
) -> bool:
    has_any_of = criteria.any_of
    has_each_user = criteria.each_user_completed_at_least
    has_phase_duration = criteria.phase_duration_at_least
    has_avg_duration = criteria.average_duration_more_than
    has_failures = criteria.failures_more_than

    if (
        not has_any_of
        and not has_each_user
        and not has_phase_duration
        and not has_avg_duration
        and not has_failures
    ):
        raise NotImplementedError(
            "No supported criteria specified in ThroughputStabilityCriteria"
        )

    if has_any_of and criteria.any_of:
        if not any(
            check_stability_criteria(
                child,
                operations,
                virtual_users,
                phase_start_time,
                now,
                step_start_time,
                counters,
                phase_ops_start,
            )
            for child in criteria.any_of
        ):
            return False

    if has_each_user and criteria.each_user_completed_at_least:
        req_count = criteria.each_user_completed_at_least.count
        req_ops = set(criteria.each_user_completed_at_least.operations)

        counter, new_ops = _consume_new_ops(
            counters,
            (id(criteria), "each_user", phase_start_time),
            operations,
            phase_ops_start,
        )
        for op in new_ops:
            if (
                op.completed_at.datetime < phase_start_time
                or op.completed_at.datetime > now
                or op.initiated_at.datetime < step_start_time
            ):
                continue
            if op.successful and str(op.type) in req_ops:
                counter.counts_by_key[op.origin] = (
                    counter.counts_by_key.get(op.origin, 0) + 1
                )

        if not all(
            counter.counts_by_key.get(vu.user_id, 0) >= req_count
            for vu in virtual_users
        ):
            return False

    if has_phase_duration and criteria.phase_duration_at_least:
        required_duration = criteria.phase_duration_at_least.timedelta
        if now - phase_start_time < required_duration:
            return False

    if has_avg_duration and criteria.average_duration_more_than:
        required_duration_s = (
            criteria.average_duration_more_than.duration.timedelta.total_seconds()
        )
        relevant_ops = set(criteria.average_duration_more_than.operations)
        counter, new_ops = _consume_new_ops(
            counters,
            (id(criteria), "avg_duration", phase_start_time),
            operations,
            phase_ops_start,
        )
        for op in new_ops:
            if (
                op.successful
                and op.type in relevant_ops
                and phase_start_time <= op.completed_at.datetime <= now
                and op.initiated_at.datetime >= step_start_time
            ):
                counter.count += 1
                counter.total_s += (
                    op.completed_at.datetime - op.initiated_at.datetime
                ).total_seconds()
        if not counter.count:
            return False
        if counter.total_s / counter.count <= required_duration_s:
            return False

    if has_failures and criteria.failures_more_than:
        req_count = criteria.failures_more_than.count
        relevant_ops = set(criteria.failures_more_than.operations)
        counter, new_ops = _consume_new_ops(
            counters,
            (id(criteria), "failures", phase_start_time),
            operations,
            phase_ops_start,
        )
        for op in new_ops:
            if (
                not op.successful
                and op.type in relevant_ops
                and op.completed_at.datetime >= phase_start_time
                and op.completed_at.datetime <= now
                and op.initiated_at.datetime >= step_start_time
            ):
                counter.count += 1
        if counter.count <= req_count:
            return False

    return True


def check_step_completion_criteria(
    criteria: StepCompletionCriteria,
    step_start_time: datetime,
    stability_time: datetime | None,
    now: datetime,
    operations: list[ExecutedOperation],
    counters: dict[tuple, OpsCounter] | None = None,
    step_ops_start: int = 0,
    stability_ops_start: int = 0,
) -> bool:
    has_any_of = criteria.any_of
    has_duration = criteria.sampling_duration_at_least
    has_completed_ops = criteria.completed_at_least
    has_min_average = criteria.average_duration_more_than
    has_stability_duration = criteria.throughput_stability_took_longer_than
    has_failures = criteria.failures_more_than

    if (
        not has_any_of
        and not has_duration
        and not has_completed_ops
        and not has_min_average
        and not has_stability_duration
        and not has_failures
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
                counters,
                step_ops_start,
                stability_ops_start,
            )
            for child in criteria.any_of
        ):
            return False

    if has_duration and criteria.sampling_duration_at_least:
        if not stability_time:
            return False
        required_duration = criteria.sampling_duration_at_least.timedelta
        if now - stability_time < required_duration:
            return False

    if has_completed_ops and criteria.completed_at_least:
        req_count = criteria.completed_at_least.count
        relevant_ops = set(criteria.completed_at_least.operations)
        completed = 0
        if stability_time:
            counter, new_ops = _consume_new_ops(
                counters,
                (id(criteria), "completed", stability_time),
                operations,
                stability_ops_start,
            )
            for op in new_ops:
                if (
                    op.successful
                    and op.completed_at.datetime >= stability_time
                    and op.type in relevant_ops
                    and op.completed_at.datetime <= now
                ):
                    counter.count += 1
            completed = counter.count
        if completed < req_count:
            return False

    if has_min_average and criteria.average_duration_more_than:
        required_duration_s = (
            criteria.average_duration_more_than.duration.timedelta.total_seconds()
        )
        relevant_ops = set(criteria.average_duration_more_than.operations)
        if not stability_time:
            return False
        counter, new_ops = _consume_new_ops(
            counters,
            (id(criteria), "avg_duration", stability_time),
            operations,
            stability_ops_start,
        )
        for op in new_ops:
            if (
                op.successful
                and op.type in relevant_ops
                and stability_time <= op.completed_at.datetime <= now
            ):
                counter.count += 1
                counter.total_s += (
                    op.completed_at.datetime - op.initiated_at.datetime
                ).total_seconds()
        if not counter.count:
            return False
        if counter.total_s / counter.count <= required_duration_s:
            return False

    if has_stability_duration and criteria.throughput_stability_took_longer_than:
        if not stability_time:
            return False
        required_duration = criteria.throughput_stability_took_longer_than.timedelta
        if stability_time - step_start_time <= required_duration:
            return False

    if has_failures and criteria.failures_more_than:
        req_count = criteria.failures_more_than.count
        relevant_ops = set(criteria.failures_more_than.operations)
        counter, new_ops = _consume_new_ops(
            counters, ("step_failures",), operations, step_ops_start
        )
        for op in new_ops:
            if (
                not op.successful
                and op.completed_at.datetime >= step_start_time
                and op.completed_at.datetime <= now
            ):
                counter.counts_by_key[op.type] = (
                    counter.counts_by_key.get(op.type, 0) + 1
                )
        fails = sum(counter.counts_by_key.get(t, 0) for t in relevant_ops)
        if fails <= req_count:
            return False

    return True


def check_load_completion_criteria(
    criteria: LoadCompletionCriteria,
    steps: list[BenchmarkScenarioStepReport],
    operations: list[ExecutedOperation],
) -> bool:
    has_any_of = criteria.any_of
    has_throughput = criteria.throughput_lower_than_peak
    has_failures = criteria.failures_more_than
    has_step_count = criteria.completed_steps
    has_most_recent_step = criteria.most_recent_step

    if (
        not has_any_of
        and not has_throughput
        and not has_failures
        and not has_step_count
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

    if has_step_count and criteria.completed_steps:
        if len(steps) < criteria.completed_steps:
            return False

    if has_most_recent_step and criteria.most_recent_step:
        if not steps:
            return False
        last_step = steps[-1]
        step_start_time = last_step.start_time.datetime
        stability_time = (
            last_step.throughput_stability_time.datetime
            if last_step.throughput_stability_time
            else None
        )
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
