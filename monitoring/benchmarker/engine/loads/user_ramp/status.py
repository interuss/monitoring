from datetime import UTC, datetime

from monitoring.benchmarker.configurations.loads import UserRampLoad
from monitoring.benchmarker.engine.loads.status import format_step_completion_progress
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.engine.users.framework import VirtualUser


def format_waiting_status(
    ramp: UserRampLoad,
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
            "each_user_completed_at_least" in ramp.throughput_stability_criteria
            and ramp.throughput_stability_criteria.each_user_completed_at_least
        ):
            crit = ramp.throughput_stability_criteria.each_user_completed_at_least
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
                ramp.step_completion_criteria,
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
