from implicitdict import StringBasedDateTime, dataclass
from loguru import logger

from monitoring.benchmarker.configurations.loads import OperationType
from monitoring.benchmarker.reports.report import (
    BenchmarkOperation,
    OperationsByOrigin,
    OperationsByOutcome,
    OperationsByType,
)
from monitoring.monitorlib.fetch import Query


@dataclass
class ExecutedOperation:
    """Record of an operation executed during a benchmark run, including type, origin, and outcome."""

    type: OperationType
    """The type of operation described by this record."""

    origin: str
    """Source/originator of this operation; e.g., the user that initiated this operation."""

    initiated_at: StringBasedDateTime
    """Time this operation was started/initiated."""

    completed_at: StringBasedDateTime
    """Time this operation completed, either successfully or in failure."""

    successful: bool
    """Whether this operation was successful (false for errors)."""

    query: Query | None = None
    """The query details for this operation, if this was a query operation and query details are being recorded."""


def group_operations(executed_ops: list[ExecutedOperation]) -> list[OperationsByType]:
    """Convert/group a flat list of ExecutedOperation into hierarchical OperationsByType structure for reports or analysis."""
    ops_by_type_origin: dict[tuple[OperationType, str], list[ExecutedOperation]] = {}
    type_order: list[OperationType] = []
    origin_order_by_type: dict[OperationType, list[str]] = {}

    for op in executed_ops:
        if op.type not in type_order:
            type_order.append(op.type)
            origin_order_by_type[op.type] = []
        if op.origin not in origin_order_by_type[op.type]:
            origin_order_by_type[op.type].append(op.origin)

        key = (op.type, op.origin)
        if key not in ops_by_type_origin:
            ops_by_type_origin[key] = []
        ops_by_type_origin[key].append(op)

    result: list[OperationsByType] = []
    for op_type in type_order:
        origins_list: list[OperationsByOrigin] = []
        for origin in origin_order_by_type[op_type]:
            ops = ops_by_type_origin[(op_type, origin)]
            successful_ops: list[BenchmarkOperation] = []
            unsuccessful_ops: list[BenchmarkOperation] = []
            for op in ops:
                clean_op = BenchmarkOperation(
                    t0=op.initiated_at,
                    t1=op.completed_at,
                )
                if op.query:
                    clean_op.query = op.query
                if op.successful:
                    successful_ops.append(clean_op)
                else:
                    unsuccessful_ops.append(clean_op)

            kwargs = {}
            if successful_ops:
                kwargs["successful"] = successful_ops
            if unsuccessful_ops:
                kwargs["unsuccessful"] = unsuccessful_ops
            outcome_record = OperationsByOutcome(**kwargs)
            origins_list.append(
                OperationsByOrigin(
                    origin=origin,
                    outcomes=[outcome_record],
                )
            )
        result.append(
            OperationsByType(
                type=op_type,
                origins=origins_list,
            )
        )
    return result


def record_operation(
    op: ExecutedOperation, operations: list[ExecutedOperation]
) -> None:
    operations.append(op)
    if not op.successful:
        if op.query is not None:
            details = (
                op.query.failure_details
                or op.query.error_message
                or op.query.response.failure
                or f"HTTP {op.query.status_code}"
            )
            logger.warning(
                f"Operation '{op.type}' from origin '{op.origin}' failed on {op.query.request.method} {op.query.request.url} ({op.query.status_code}): {details}"
            )
        else:
            logger.warning(f"Operation '{op.type}' from origin '{op.origin}' failed.")
