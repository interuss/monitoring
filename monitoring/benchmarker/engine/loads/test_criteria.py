import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.benchmarker.configurations.loads import (
    OperationType,
    ThroughputStabilityCriteria,
    WorkflowType,
)
from monitoring.benchmarker.configurations.users import BenchmarkUserName
from monitoring.benchmarker.engine.coordination import Coordinator
from monitoring.benchmarker.engine.loads.criteria import check_stability_criteria
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.engine.users.framework import VirtualUser

STEP_START = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
NOW = STEP_START + timedelta(seconds=60)
FLIGHT = "workflow.flight_planner.flight"


class _User(VirtualUser):
    async def run_custom_workflow(self, stop_event: asyncio.Event) -> None:
        pass

    async def cleanup(self) -> None:
        pass


def _flight(origin: str, initiated_at: datetime, successful: bool) -> ExecutedOperation:
    return ExecutedOperation(
        type=OperationType(WorkflowType.FlightPlannerFlight),
        origin=origin,
        initiated_at=StringBasedDateTime(initiated_at),
        completed_at=StringBasedDateTime(STEP_START + timedelta(seconds=10)),
        successful=successful,
        query=None,
    )


def _check(
    criteria: dict, operations: list[ExecutedOperation], users: list[str]
) -> bool:
    return check_stability_criteria(
        ImplicitDict.parse(criteria, ThroughputStabilityCriteria),
        operations,
        [
            _User(
                u,
                BenchmarkUserName("FPU"),
                ThreadPoolExecutor(max_workers=1),
                Coordinator([]),
                lambda op: None,
            )
            for u in users
        ],
        STEP_START,
        NOW,
        STEP_START,
    )


# This test is AI-generated and has not been closely inspected by a human.
@pytest.mark.parametrize("initiated_offset_s,expected", [(-70, False), (1, True)])
def test_failures_more_than_only_counts_operations_initiated_in_step(
    initiated_offset_s, expected
):
    t0 = STEP_START + timedelta(seconds=initiated_offset_s)
    ops = [_flight(f"user_{i}", t0, False) for i in range(5)]
    criteria = {"failures_more_than": {"count": 2, "operations": [FLIGHT]}}
    assert _check(criteria, ops, []) == expected


# This test is AI-generated and has not been closely inspected by a human.
@pytest.mark.parametrize("initiated_offset_s,expected", [(-70, False), (1, True)])
def test_average_duration_more_than_only_counts_operations_initiated_in_step(
    initiated_offset_s, expected
):
    t0 = STEP_START + timedelta(seconds=initiated_offset_s)
    ops = [_flight(f"user_{i}", t0, True) for i in range(5)]
    criteria = {
        "average_duration_more_than": {"duration": "5s", "operations": [FLIGHT]}
    }
    assert _check(criteria, ops, []) == expected


# This test is AI-generated and has not been closely inspected by a human.
@pytest.mark.parametrize("initiated_offset_s,expected", [(-70, False), (1, True)])
def test_each_user_completed_at_least_only_counts_operations_initiated_in_step(
    initiated_offset_s, expected
):
    t0 = STEP_START + timedelta(seconds=initiated_offset_s)
    users = [f"user_{i}" for i in range(3)]
    ops = [_flight(u, t0, True) for u in users]
    criteria = {"each_user_completed_at_least": {"count": 1, "operations": [FLIGHT]}}
    assert _check(criteria, ops, users) == expected
