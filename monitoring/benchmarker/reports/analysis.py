from collections.abc import Iterable, Sequence
from datetime import datetime

from monitoring.benchmarker.configurations.loads import OperationType
from monitoring.benchmarker.reports.report import (
    BenchmarkOperation,
    BenchmarkScenarioReport,
    OperationsByOrigin,
    OperationsByOutcome,
    OperationsByType,
)

OperationsHierarchyMember = (
    Sequence[OperationsByType]
    | OperationsByType
    | OperationsByOrigin
    | OperationsByOutcome
    | BenchmarkOperation
)


def select_operations(
    operations: OperationsHierarchyMember,
    types: Sequence[OperationType | str] | None = None,
    origins: Sequence[str] | None = None,
    outcomes: Sequence[bool] | None = None,
    completed_after: datetime | None = None,
    completed_before: datetime | None = None,
) -> Iterable[BenchmarkOperation]:
    def nest(sub_operations):
        for op in sub_operations:
            yield from select_operations(
                op, types, origins, outcomes, completed_after, completed_before
            )

    if isinstance(operations, Sequence):
        yield from nest(operations)
    elif isinstance(operations, OperationsByType):
        norm_types = {OperationType(t) for t in types} if types is not None else None
        types_match = (
            norm_types is None
            or operations.type in norm_types
            or str(operations.type) in {str(t) for t in norm_types}
        )
        if types_match:
            yield from nest(operations.origins)
    elif isinstance(operations, OperationsByOrigin):
        if origins is None or operations.origin in origins:
            yield from nest(operations.outcomes)
    elif isinstance(operations, OperationsByOutcome):
        if "successful" in operations and operations.successful:
            if outcomes is None or True in outcomes:
                yield from nest(operations.successful)
        if "unsuccessful" in operations and operations.unsuccessful:
            if outcomes is None or False in outcomes:
                yield from nest(operations.unsuccessful)
    elif isinstance(operations, BenchmarkOperation):
        if completed_after and operations.t1.datetime < completed_after:
            return
        if completed_before and operations.t1.datetime > completed_before:
            return
        yield operations
    else:
        raise ValueError(
            f"`operations` type '{type(operations).__name__}' is not valid"
        )


def throughput_of_operations(
    operations: OperationsHierarchyMember,
    start_time: datetime,
    end_time: datetime,
    **kwargs,
) -> float:
    """Determine the achieved throughput during a specified time range from a list of completed operations.

    Args:
      * operations: List of relevant operations over all time.
      * start_time: Beginning of time window in which to inspect throughput.
      * end_time: End of time window in which to inspect throughput.

    Returns: Throughput in operations of interest per second.

    Notes:
      Operation flux must have already been in steady-state at `start_time` for this throughput calculation to be
      valid.  What happens after `end_time` does not affect this calculation.  "Partial credit" is not given for
      eventually-successful operations in progress at `end_time` as attempting to do so would require operation
      flux to remain in steady-state after `end_time` until completion of the last operation started before
      `end_time` for the throughput calculation to be valid.  Instead, the partial work of operations in progress
      at `end_time` effectively discarded by this approach should be (statistically) exactly balanced by the
      partial work included "for free" of operations started before `start_time` that end within the time window.
    """
    dur = (end_time - start_time).total_seconds()
    kwargs["outcomes"] = (True,)
    kwargs["completed_after"] = start_time
    kwargs["completed_before"] = end_time
    return (
        sum(1 for _ in select_operations(operations, **kwargs)) / dur
        if dur > 0
        else 0.0
    )


def throughput_of_step(
    report: BenchmarkScenarioReport, step_index: int, **kwargs
) -> float:
    step = report.steps[step_index]
    return throughput_of_operations(
        report.operations,
        step.throughput_stability_time.datetime,
        step.end_time.datetime,
        **kwargs,
    )
