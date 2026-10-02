import math
from dataclasses import dataclass

from monitoring.benchmarker.configurations.loads import (
    SearchCompletionCriteria,
    StepCompletionCriteria,
    UserSearchLoad,
)
from monitoring.benchmarker.engine.loads.status import (
    get_operations_of_interest,
    throughput_of_step_ops,
)
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.reports.report import (
    BenchmarkScenarioStepReport,
    StepTerminationReason,
)


@dataclass
class MeasuredStep:
    users: int
    is_stable: bool
    throughput: float


def _round_half_up(val: float) -> int:
    return int(math.floor(val + 0.5))


def build_measured_steps(
    steps: list[BenchmarkScenarioStepReport],
    operations: list[ExecutedOperation],
    step_completion_criteria: StepCompletionCriteria,
) -> dict[int, MeasuredStep]:
    """Summarize completed and unstable steps keyed by integer user count."""
    measured: dict[int, MeasuredStep] = {}
    for step in steps:
        users = int(round(step.load_factor))
        is_stable = step.termination_reason == StepTerminationReason.Completed
        if is_stable:
            step_ops = [
                op
                for op in operations
                if op.completed_at.datetime >= step.start_time.datetime
                and op.completed_at.datetime <= step.end_time.datetime
            ]
            ops_of_interest = get_operations_of_interest(
                step_completion_criteria, step_ops, True
            )
            tp = throughput_of_step_ops(step, operations, ops_of_interest)
        else:
            tp = 0.0
        measured[users] = MeasuredStep(users=users, is_stable=is_stable, throughput=tp)
    return measured


def _get_adjacency(criteria: SearchCompletionCriteria) -> int:
    adj = (
        criteria.adjacency_user_count
        if "adjacency_user_count" in criteria
        and criteria.adjacency_user_count is not None
        else 1
    )
    if adj < 1:
        raise ValueError(f"adjacency_user_count must be >= 1, got {adj}")
    return adj


def _validate_search_criteria(criteria: SearchCompletionCriteria) -> None:
    if "any_of" in criteria and criteria.any_of:
        raise NotImplementedError("SearchCompletionCriteria.any_of is not implemented")

    has_consec_stable = (
        "consecutive_stable_user_counts" in criteria
        and criteria.consecutive_stable_user_counts is not None
    )
    has_consec_unstable = (
        "consecutive_unstable_user_counts" in criteria
        and criteria.consecutive_unstable_user_counts is not None
    )
    has_max_tp_adj = (
        "max_throughput_adjacent_user_counts" in criteria
        and criteria.max_throughput_adjacent_user_counts is not None
    )
    has_left_spacing = (
        "maximum_left_side_spacing" in criteria
        and criteria.maximum_left_side_spacing is not None
    )

    if (
        not has_consec_stable
        and not has_consec_unstable
        and not has_max_tp_adj
        and not has_left_spacing
    ):
        raise NotImplementedError(
            "SearchCompletionCriteria specified no supported conditions"
        )


def _stable_run_ending_at(
    sorted_users: list[int],
    measured: dict[int, MeasuredStep],
    end_idx: int,
    adj: int,
) -> list[int]:
    """Return the chain of consecutive stable user counts ending at sorted_users[end_idx]."""
    if not measured[sorted_users[end_idx]].is_stable:
        return []
    run = [sorted_users[end_idx]]
    idx = end_idx
    while idx > 0:
        prev_u = sorted_users[idx - 1]
        curr_u = sorted_users[idx]
        if measured[prev_u].is_stable and curr_u - prev_u <= adj:
            run.append(prev_u)
            idx -= 1
        else:
            break
    run.reverse()
    return run


def _unstable_run_starting_at(
    sorted_users: list[int],
    measured: dict[int, MeasuredStep],
    start_idx: int,
    adj: int,
) -> list[int]:
    """Return the chain of consecutive unstable user counts starting at sorted_users[start_idx]."""
    if measured[sorted_users[start_idx]].is_stable:
        return []
    run = [sorted_users[start_idx]]
    idx = start_idx
    while idx + 1 < len(sorted_users):
        curr_u = sorted_users[idx]
        next_u = sorted_users[idx + 1]
        if not measured[next_u].is_stable and next_u - curr_u <= adj:
            run.append(next_u)
            idx += 1
        else:
            break
    return run


def _is_consecutive_stable_satisfied(
    sorted_users: list[int],
    measured: dict[int, MeasuredStep],
    req_stable: int,
    adj: int,
) -> bool:
    if req_stable <= 0:
        return True
    for idx in range(len(sorted_users) - 1):
        u_curr = sorted_users[idx]
        u_next = sorted_users[idx + 1]
        if (
            measured[u_curr].is_stable
            and not measured[u_next].is_stable
            and u_next - u_curr <= adj
        ):
            run = _stable_run_ending_at(sorted_users, measured, idx, adj)
            if len(run) >= req_stable:
                return True
    return False


def _is_consecutive_unstable_satisfied(
    sorted_users: list[int],
    measured: dict[int, MeasuredStep],
    req_unstable: int,
    adj: int,
) -> bool:
    if req_unstable <= 0:
        return True
    for idx in range(len(sorted_users) - 1):
        u_curr = sorted_users[idx]
        u_next = sorted_users[idx + 1]
        if (
            measured[u_curr].is_stable
            and not measured[u_next].is_stable
            and u_next - u_curr <= adj
        ):
            run = _unstable_run_starting_at(sorted_users, measured, idx + 1, adj)
            if len(run) >= req_unstable:
                return True
    return False


def _next_user_for_stability_boundary(
    sorted_users: list[int],
    measured: dict[int, MeasuredStep],
    req_stable: int,
    req_unstable: int,
    adj: int,
    expansion_ratio: float,
) -> int | None:
    """Determine the next user count to satisfy consecutive_stable_user_counts and consecutive_unstable_user_counts.

    Returns None if both are satisfied.
    """
    stable_ok = _is_consecutive_stable_satisfied(
        sorted_users, measured, req_stable, adj
    )
    unstable_ok = _is_consecutive_unstable_satisfied(
        sorted_users, measured, req_unstable, adj
    )
    if stable_ok and unstable_ok:
        return None

    stable_indices = [i for i, u in enumerate(sorted_users) if measured[u].is_stable]
    if not stable_indices:
        min_u = sorted_users[0]
        if min_u <= 1:
            raise RuntimeError(
                "No stable step found and minimum tested user count is already <= 1"
            )
        return max(1, min_u // 2)

    s_top_idx = stable_indices[-1]
    s_top = sorted_users[s_top_idx]

    # If there is no measured step above the highest stable step, expand upward
    if s_top_idx == len(sorted_users) - 1:
        u_max = sorted_users[-1]
        return max(_round_half_up(u_max * expansion_ratio), u_max + adj)

    # Since s_top is the highest stable step, sorted_users[s_top_idx + 1] is guaranteed to be unstable
    u_next_idx = s_top_idx + 1
    u_next = sorted_users[u_next_idx]

    # Binary search until the stable/unstable boundary is within adjacency_user_count
    if u_next - s_top > adj:
        return (s_top + u_next) // 2

    # First satisfy consecutive_stable_user_counts if needed
    if not stable_ok:
        # Check candidate (stable, unstable) boundaries from highest to lowest
        for s_idx in reversed(stable_indices):
            if s_idx + 1 >= len(sorted_users):
                continue
            s_u = sorted_users[s_idx]
            next_u = sorted_users[s_idx + 1]
            if measured[next_u].is_stable:
                continue
            if next_u - s_u > adj:
                return (s_u + next_u) // 2

            run = _stable_run_ending_at(sorted_users, measured, s_idx, adj)
            s_bottom = run[0]
            candidate = s_bottom - adj
            # Check if candidate is valid and not blocked by an already-measured step
            u_blocker = max(
                (u for u in sorted_users if u < s_bottom and not measured[u].is_stable),
                default=0,
            )
            max_additional_steps = (s_bottom - u_blocker - 1) // adj
            if candidate > u_blocker and len(run) + max_additional_steps >= req_stable:
                return candidate

        raise RuntimeError(
            f"Unable to find {req_stable} consecutive stable user counts before instability"
        )

    # Next satisfy consecutive_unstable_user_counts if needed
    if not unstable_ok:
        run = _unstable_run_starting_at(sorted_users, measured, u_next_idx, adj)
        u_top_run = run[-1]
        return u_top_run + adj

    return None


def _next_user_for_max_throughput(
    sorted_users: list[int],
    measured: dict[int, MeasuredStep],
    req_tp_adj: int,
    adj: int,
    expansion_ratio: float,
) -> int | None:
    """Determine the next user count to satisfy max_throughput_adjacent_user_counts.

    Returns None if satisfied.
    """
    if req_tp_adj <= 0:
        return None

    stable_steps = [measured[u] for u in sorted_users if measured[u].is_stable]
    if not stable_steps:
        raise RuntimeError(
            "Cannot determine maximum throughput without at least one stable step"
        )

    peak_step = max(stable_steps, key=lambda s: (s.throughput, s.users))
    u_peak = peak_step.users

    # If no step above u_peak has been measured yet, expand upward first to bracket the peak
    if u_peak == sorted_users[-1]:
        u_max = sorted_users[-1]
        return max(_round_half_up(u_max * expansion_ratio), u_max + adj)

    # 1. Check upper portion of max_throughput_adjacent_user_counts
    curr = u_peak
    for _ in range(req_tp_adj):
        higher = [u for u in sorted_users if u > curr]
        u_next = higher[0] if higher else None
        if u_next is not None and u_next - curr <= adj:
            if not measured[u_next].is_stable:
                # Encountered an unstable step; upper portion is complete
                break
            curr = u_next
        else:
            return curr + adj

    # 2. Check lower portion of max_throughput_adjacent_user_counts
    curr = u_peak
    for _ in range(req_tp_adj):
        lower = [u for u in sorted_users if u < curr]
        u_prev = lower[-1] if lower else None
        if u_prev is not None and curr - u_prev <= adj:
            if not measured[u_prev].is_stable:
                # Encountered an unstable step; lower portion is complete
                break
            curr = u_prev
        else:
            if curr - adj < 1:
                break
            return curr - adj

    return None


def _next_user_for_left_side_spacing(
    sorted_users: list[int],
    measured: dict[int, MeasuredStep],
    max_spacing_frac: float | None,
) -> int | None:
    """Determine the next user count to satisfy maximum_left_side_spacing.

    Returns None if satisfied.
    """
    if max_spacing_frac is None:
        return None
    if max_spacing_frac <= 0:
        raise ValueError(
            f"maximum_left_side_spacing must be positive, got {max_spacing_frac}"
        )

    stable_steps = [measured[u] for u in sorted_users if measured[u].is_stable]
    if not stable_steps:
        raise RuntimeError(
            "Cannot evaluate maximum_left_side_spacing without at least one stable step"
        )

    peak_step = max(stable_steps, key=lambda s: (s.throughput, s.users))
    u_peak = peak_step.users

    max_int_gap = max(1, int(math.floor(max_spacing_frac * u_peak + 1e-9)))
    left_points = [0] + [u for u in sorted_users if u <= u_peak]

    for i in range(len(left_points) - 1):
        u_a = left_points[i]
        u_b = left_points[i + 1]
        gap = u_b - u_a
        if gap > max_int_gap:
            num_intervals = math.ceil(gap / max_int_gap)
            step_offset = max(1, _round_half_up(gap / num_intervals))
            candidate = min(u_b - 1, u_a + step_offset)
            return candidate

    return None


def determine_next_user_count(
    search: UserSearchLoad,
    steps: list[BenchmarkScenarioStepReport],
    operations: list[ExecutedOperation],
) -> int | None:
    """Determine the next user count to evaluate for a UserSearchLoad, or None if search is complete."""
    criteria = search.search_completion_criteria
    _validate_search_criteria(criteria)

    if not steps:
        return search.initial_users

    measured = build_measured_steps(steps, operations, search.step_completion_criteria)
    sorted_users = sorted(measured.keys())
    adj = _get_adjacency(criteria)
    expansion_ratio = (
        search.user_expansion_ratio
        if "user_expansion_ratio" in search and search.user_expansion_ratio
        else 2.0
    )

    # 1. Stability boundary search (consecutive_stable_user_counts & consecutive_unstable_user_counts)
    req_stable = (
        criteria.consecutive_stable_user_counts
        if "consecutive_stable_user_counts" in criteria
        and criteria.consecutive_stable_user_counts is not None
        else 0
    )
    req_unstable = (
        criteria.consecutive_unstable_user_counts
        if "consecutive_unstable_user_counts" in criteria
        and criteria.consecutive_unstable_user_counts is not None
        else 0
    )
    if req_stable > 0 or req_unstable > 0:
        next_u = _next_user_for_stability_boundary(
            sorted_users,
            measured,
            req_stable,
            req_unstable,
            adj,
            expansion_ratio,
        )
        if next_u is not None:
            return next_u

    # 2. Maximum throughput search (max_throughput_adjacent_user_counts)
    req_tp_adj = (
        criteria.max_throughput_adjacent_user_counts
        if "max_throughput_adjacent_user_counts" in criteria
        and criteria.max_throughput_adjacent_user_counts is not None
        else 0
    )
    if req_tp_adj > 0:
        next_u = _next_user_for_max_throughput(
            sorted_users,
            measured,
            req_tp_adj,
            adj,
            expansion_ratio,
        )
        if next_u is not None:
            return next_u

    # 3. Left-side spacing gap filling (maximum_left_side_spacing)
    max_spacing_frac = (
        criteria.maximum_left_side_spacing
        if "maximum_left_side_spacing" in criteria
        and criteria.maximum_left_side_spacing is not None
        else None
    )
    if max_spacing_frac is not None:
        next_u = _next_user_for_left_side_spacing(
            sorted_users,
            measured,
            max_spacing_frac,
        )
        if next_u is not None:
            return next_u

    return None


def check_search_completion_criteria(
    search: UserSearchLoad,
    steps: list[BenchmarkScenarioStepReport],
    operations: list[ExecutedOperation],
) -> bool:
    """Return True if all search_completion_criteria in UserSearchLoad are satisfied."""
    return determine_next_user_count(search, steps, operations) is None
