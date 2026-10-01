import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.benchmarker.configurations.loads import (
    OperationType,
    UserSearchLoad,
    WorkflowType,
)
from monitoring.benchmarker.configurations.scenarios import BenchmarkScenarioName
from monitoring.benchmarker.configurations.users import (
    BenchmarkUserName,
    BenchmarkUserSpecification,
)
from monitoring.benchmarker.engine.coordination import Coordinator
from monitoring.benchmarker.engine.loads.user_search.search import (
    check_search_completion_criteria,
    determine_next_user_count,
)
from monitoring.benchmarker.engine.loads.user_search.user_search import (
    run_user_search_load,
)
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.engine.users.framework import VirtualUser
from monitoring.benchmarker.reports.report import (
    BenchmarkScenarioStepReport,
    StepTerminationReason,
)
from monitoring.benchmarker.validation import load_config


def _make_step_and_ops(
    step_idx: int,
    users: int,
    is_stable: bool,
    throughput: float,
) -> tuple[BenchmarkScenarioStepReport, list[ExecutedOperation]]:
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(
        minutes=step_idx * 5
    )
    start_time = base_time
    if not is_stable:
        return (
            BenchmarkScenarioStepReport(
                load_factor=float(users),
                start_time=StringBasedDateTime(start_time),
                throughput_stability_time=None,
                end_time=StringBasedDateTime(start_time + timedelta(seconds=10)),
                termination_reason=StepTerminationReason.StabilityNotAchieved,
            ),
            [],
        )

    stability_time = start_time + timedelta(seconds=5)
    # Use a 100s sampling window so throughput * 100 operations produce the exact throughput
    end_time = stability_time + timedelta(seconds=100)
    num_ops = int(round(throughput * 100))
    ops = [
        ExecutedOperation(
            type=OperationType(WorkflowType.FlightPlannerFlight),
            origin=f"user_{i}",
            initiated_at=StringBasedDateTime(stability_time + timedelta(seconds=1)),
            completed_at=StringBasedDateTime(stability_time + timedelta(seconds=2)),
            successful=True,
            query=None,
        )
        for i in range(num_ops)
    ]
    step = BenchmarkScenarioStepReport(
        load_factor=float(users),
        start_time=StringBasedDateTime(start_time),
        throughput_stability_time=StringBasedDateTime(stability_time),
        end_time=StringBasedDateTime(end_time),
        termination_reason=StepTerminationReason.Completed,
    )
    return step, ops


def _make_search_load(
    initial_users: int = 1,
    user_expansion_ratio: float = 2.0,
    adjacency_user_count: int = 1,
    consecutive_stable: int | None = 3,
    consecutive_unstable: int | None = 3,
    max_tp_adjacent: int | None = 3,
    max_left_spacing: float | None = 0.1,
) -> UserSearchLoad:
    criteria_dict: dict = {"adjacency_user_count": adjacency_user_count}
    if consecutive_stable is not None:
        criteria_dict["consecutive_stable_user_counts"] = consecutive_stable
    if consecutive_unstable is not None:
        criteria_dict["consecutive_unstable_user_counts"] = consecutive_unstable
    if max_tp_adjacent is not None:
        criteria_dict["max_throughput_adjacent_user_counts"] = max_tp_adjacent
    if max_left_spacing is not None:
        criteria_dict["maximum_left_side_spacing"] = max_left_spacing

    return ImplicitDict.parse(
        {
            "user_type": "FPU1",
            "initial_users": initial_users,
            "user_expansion_ratio": user_expansion_ratio,
            "throughput_stability_criteria": {
                "each_user_completed_at_least": {
                    "count": 1,
                    "operations": ["workflow.flight_planner.flight"],
                }
            },
            "step_completion_criteria": {
                "completed_at_least": {
                    "count": 5,
                    "operations": ["workflow.flight_planner.flight"],
                }
            },
            "search_completion_criteria": criteria_dict,
        },
        UserSearchLoad,
    )


# This test is AI-generated and has not been closely inspected by a human.
def test_prompt_walkthrough_when_45_is_unstable():
    """Verify the exact step sequence from the user's specification when 45 users is unstable."""
    search = _make_search_load()

    # Define system behavior matching the prompt narrative:
    # - Stable for <= 42 users, unstable for >= 43 users
    # - Throughput peaks at 32 among initial powers of 2, then 33 > 32, then 31 > 33
    def simulate(users: int) -> tuple[bool, float]:
        is_stable = users <= 42
        if not is_stable:
            return False, 0.0
        throughputs = {
            32: 100.0,
            33: 105.0,
            34: 102.0,
            35: 101.0,
            36: 100.0,
            31: 110.0,
            30: 108.0,
            29: 107.0,
            28: 106.0,
        }
        return True, throughputs.get(users, float(users) * 2.0)

    steps: list[BenchmarkScenarioStepReport] = []
    operations: list[ExecutedOperation] = []
    chosen_users: list[int] = []

    while True:
        next_u = determine_next_user_count(search, steps, operations)
        if next_u is None:
            break
        chosen_users.append(next_u)
        stable, tp = simulate(next_u)
        step, ops = _make_step_and_ops(len(steps), next_u, stable, tp)
        steps.append(step)
        operations.extend(ops)

    expected_sequence = [
        # Expansion phase
        1,
        2,
        4,
        8,
        16,
        32,
        64,
        # Binary search for instability boundary
        48,
        40,
        44,
        42,
        43,
        # Satisfy consecutive_stable_user_counts=3 (40, 41, 42 before 43)
        41,
        # Satisfy consecutive_unstable_user_counts=3 (43, 44, 45 after 42)
        45,
        # Max throughput search: 32 is peak -> try 33 (new peak) -> 34, 35, 36 -> 31 (new peak) -> 30, 29, 28
        33,
        34,
        35,
        36,
        31,
        30,
        29,
        28,
        # Left-side spacing (max gap = floor(0.1 * 31) = 3):
        # Gap (4, 8) -> 6; Gap (8, 16) -> 11, 14; Gap (16, 28) -> 19, 22, 25
        6,
        11,
        14,
        19,
        22,
        25,
    ]
    assert chosen_users == expected_sequence
    assert check_search_completion_criteria(search, steps, operations)


# This test is AI-generated and has not been closely inspected by a human.
def test_prompt_walkthrough_when_45_is_stable():
    """Verify the sequence when 45 users is unexpectedly stable, requiring 46 and 47 to be tested."""
    search = _make_search_load(max_tp_adjacent=None, max_left_spacing=None)

    def simulate(users: int) -> tuple[bool, float]:
        if users in (43, 44) or users >= 46:
            return False, 0.0
        return True, float(users)

    steps: list[BenchmarkScenarioStepReport] = []
    operations: list[ExecutedOperation] = []
    chosen_users: list[int] = []

    while True:
        next_u = determine_next_user_count(search, steps, operations)
        if next_u is None:
            break
        chosen_users.append(next_u)
        stable, tp = simulate(next_u)
        step, ops = _make_step_and_ops(len(steps), next_u, stable, tp)
        steps.append(step)
        operations.extend(ops)

    expected_sequence = [
        1,
        2,
        4,
        8,
        16,
        32,
        64,
        48,
        40,
        44,
        42,
        43,
        41,
        45,  # 45 is stable!
        46,  # unstable
        47,  # unstable -> 45 (stable) followed by 46, 47, 48 (unstable) satisfies consecutive_unstable=3
    ]
    assert chosen_users == expected_sequence
    assert check_search_completion_criteria(search, steps, operations)


# This test is AI-generated and has not been closely inspected by a human.
def test_initial_users_greater_than_1_and_adjacency_2():
    """Verify search with initial_users=16 and adjacency_user_count=2 (like isas_uncontended.jsonnet),
    including filling left-side gaps down toward 0."""
    search = _make_search_load(
        initial_users=16,
        user_expansion_ratio=2.0,
        adjacency_user_count=2,
        consecutive_stable=3,
        consecutive_unstable=3,
        max_tp_adjacent=2,
        max_left_spacing=0.2,
    )

    # Stable up to 42, unstable >= 43; peak throughput at 30
    def simulate(users: int) -> tuple[bool, float]:
        if users >= 43:
            return False, 0.0
        if users == 30:
            return True, 200.0
        if users == 32:
            return True, 180.0
        return True, float(users) * 4.0

    steps: list[BenchmarkScenarioStepReport] = []
    operations: list[ExecutedOperation] = []
    chosen_users: list[int] = []

    while True:
        next_u = determine_next_user_count(search, steps, operations)
        if next_u is None:
            break
        assert next_u not in chosen_users, f"Duplicate user count selected: {next_u}"
        chosen_users.append(next_u)
        stable, tp = simulate(next_u)
        step, ops = _make_step_and_ops(len(steps), next_u, stable, tp)
        steps.append(step)
        operations.extend(ops)

    # Verify left side down to 0 has no gap > 0.2 * 30 = 6
    left_points = [0] + sorted(u for u in chosen_users if u <= 30)
    for a, b in zip(left_points, left_points[1:], strict=False):
        assert b - a <= 6
    assert check_search_completion_criteria(search, steps, operations)


# This test is AI-generated and has not been closely inspected by a human.
def test_any_of_raises_not_implemented():
    search = ImplicitDict.parse(
        {
            "user_type": "FPU1",
            "initial_users": 1,
            "throughput_stability_criteria": {
                "each_user_completed_at_least": {
                    "count": 1,
                    "operations": ["workflow.flight_planner.flight"],
                }
            },
            "step_completion_criteria": {
                "completed_at_least": {
                    "count": 1,
                    "operations": ["workflow.flight_planner.flight"],
                }
            },
            "search_completion_criteria": {
                "any_of": [{"consecutive_stable_user_counts": 2}]
            },
        },
        UserSearchLoad,
    )
    with pytest.raises(NotImplementedError, match="any_of"):
        determine_next_user_count(search, [], [])


class _DummyVirtualUser(VirtualUser):
    def __init__(
        self, user_id, user_type_name, executor, coordinator, record_op, state
    ):
        super().__init__(user_id, user_type_name, executor, coordinator, record_op)
        self.state = state
        self.cleanup_count = 0
        self.stopped = False

    async def run_custom_workflow(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            now = datetime.now(UTC)
            active_count = self.state["active_count"]
            is_failing = active_count >= 4
            op = ExecutedOperation(
                type=OperationType(WorkflowType.FlightPlannerFlight),
                origin=self.user_id,
                initiated_at=StringBasedDateTime(now),
                completed_at=StringBasedDateTime(now + timedelta(milliseconds=10)),
                successful=not is_failing,
                query=None,
            )
            self.record_operation(op)
            await self.sleep_interruptible(0.05, stop_event)
        self.stopped = True

    async def cleanup(self) -> None:
        self.cleanup_count += 1


# This test is AI-generated and has not been closely inspected by a human.
def test_run_user_search_load_recovers_from_unstable_step():
    """Verify run_user_search_load gracefully stops and cleans up all users after an unstable step and continues."""
    search = ImplicitDict.parse(
        {
            "user_type": "FPU1",
            "initial_users": 2,
            "user_expansion_ratio": 2.0,
            "throughput_stability_criteria": {
                "each_user_completed_at_least": {
                    "count": 1,
                    "operations": ["workflow.flight_planner.flight"],
                }
            },
            "throughput_instability_criteria": {
                "failures_more_than": {
                    "count": 2,
                    "operations": ["workflow.flight_planner.flight"],
                }
            },
            "step_completion_criteria": {
                "completed_at_least": {
                    "count": 2,
                    "operations": ["workflow.flight_planner.flight"],
                }
            },
            "search_completion_criteria": {
                "consecutive_stable_user_counts": 2,
                "consecutive_unstable_user_counts": 1,
            },
        },
        UserSearchLoad,
    )

    state = {"active_count": 0, "created_users": [], "cleaned_before_step_2": False}

    def fake_create_vu(
        user_id, user_spec, resource_pool, executor, coordinator, record_op, rand
    ):
        # When spawning the first user of step 2 (after unstable step 1 with 4 users),
        # all 4 users from steps 0 and 1 must already have been stopped and cleaned up.
        if len(state["created_users"]) == 4:
            state["cleaned_before_step_2"] = all(
                u.stopped and u.cleanup_count == 1 for u in state["created_users"]
            )
        vu = _DummyVirtualUser(
            user_id, user_spec.name, executor, coordinator, record_op, state
        )
        state["created_users"].append(vu)
        state["active_count"] = sum(1 for u in state["created_users"] if not u.stopped)
        return vu

    user_specs_map = {
        BenchmarkUserName("FPU1"): ImplicitDict.parse(
            {"name": "FPU1"}, BenchmarkUserSpecification
        )
    }

    with (
        patch(
            "monitoring.benchmarker.engine.loads.user_search.user_search.create_virtual_user",
            side_effect=fake_create_vu,
        ),
        ThreadPoolExecutor(max_workers=4) as executor,
    ):
        ops, steps, cleanup = asyncio.run(
            run_user_search_load(
                search,
                user_specs_map,
                {},
                executor,
                Coordinator([]),
                BenchmarkScenarioName("test_scenario"),
            )
        )

    step_users = [int(s.load_factor) for s in steps]
    # 2 (stable) -> 4 (unstable) -> 3 (stable) -> now (2, 3) are 2 consecutive stable and (4) is 1 unstable!
    assert step_users == [2, 4, 3]
    assert steps[0].termination_reason == StepTerminationReason.Completed
    assert steps[1].termination_reason == StepTerminationReason.StabilityNotAchieved
    assert steps[2].termination_reason == StepTerminationReason.Completed
    assert state["cleaned_before_step_2"]
    assert all(u.stopped and u.cleanup_count == 1 for u in state["created_users"])


# This test is AI-generated and has not been closely inspected by a human.
def test_isas_uncontended_config_validates():
    config = load_config("configurations.interuss.netrid.isas_uncontended")
    assert len(config.loads) >= 1
    assert all(
        "user_search" in load and load.user_search is not None for load in config.loads
    )
