from typing import Optional

from implicitdict import ImplicitDict

from monitoring.benchmarker.configurations.loads import OperationType


class TimelineOperation(ImplicitDict):
    type: OperationType

    color: Optional[str]
    """CSS color (e.g., #ff1122) for this operation.  Picked automatically if not specified."""

    success_indicator_width: Optional[float]
    """Width of the termination line indicating success or failure of each of these operations."""


class TimelineSpecification(ImplicitDict):
    name: str
    """Machine-level name for this report.  Used as the output file name."""

    operations: list[TimelineOperation]
    """Operations to display on the timeline."""
