from __future__ import annotations

from enum import StrEnum
from typing import Optional

from implicitdict import ImplicitDict, StringBasedTimeDelta

from monitoring.benchmarker.configurations.users import BenchmarkUserName
from monitoring.monitorlib.fetch import QueryType


class BenchmarkLoadName(str):
    """Unique (within benchmark configuration) name for a load profile."""


class WorkflowType(StrEnum):
    """Type of operation, other than an HTTP query, providing load to a system being benchmarked."""

    FlightPlannerFlight = "flight_planner.flight"
    """An operation consisting of managing a flight from end to end, including all associated UTM actions like establishing an operational intent and deleting it."""


class OperationType(str):
    """Type of operation providing load to a system being benchmarked."""

    query_type: QueryType | None = None
    workflow_type: WorkflowType | None = None

    def __new__(
        cls, value: str | QueryType | WorkflowType | OperationType | None
    ) -> OperationType:
        if isinstance(value, OperationType):
            obj = str.__new__(cls, value)
            obj.query_type = value.query_type
            obj.workflow_type = value.workflow_type
            return obj

        query_type = None
        workflow_type = None

        if isinstance(value, QueryType):
            query_type = value
            str_val = f"query.{value.value}"
        elif isinstance(value, WorkflowType):
            workflow_type = value
            str_val = f"workflow.{value.value}"
        elif isinstance(value, str):
            if value.startswith("query."):
                raw_enum = value[len("query.") :]
                query_type = QueryType(raw_enum)
                str_val = value
            elif value.startswith("workflow."):
                raw_enum = value[len("workflow.") :]
                workflow_type = WorkflowType(raw_enum)
                str_val = value
            else:
                raise ValueError(f"Invalid OperationType string value '{value}'")
        else:
            raise ValueError(
                f"Cannot construct OperationType from {type(value).__name__} '{value}'"
            )

        obj = str.__new__(cls, str_val)
        obj.query_type = query_type
        obj.workflow_type = workflow_type
        return obj


class OperationCount(ImplicitDict):
    count: int
    """Number of matching operations."""

    operations: list[OperationType]
    """Particular operations to look for."""


class ThroughputStabilityCriteria(ImplicitDict):
    """Criteria used to determine when it is valid to start collecting throughput data in a step.

    Any specified field that evaluates to false will cause this criteria to evaluate to false"""

    each_user_completed_at_least: Optional[OperationCount]
    """Evaluates true when each user has completed at least this many operations since the step started."""


class OperationLatency(ImplicitDict):
    duration: StringBasedTimeDelta
    """Duration of relevant operations."""

    operations: list[OperationType]
    """Particular operations to look for."""


class StepCompletionCriteria(ImplicitDict):
    """Completion criteria based on a load step.

    Any specified field that evaluates to false will cause this criteria to evaluate to false."""

    any_of: Optional[list[StepCompletionCriteria]]

    sampling_duration_at_least: Optional[StringBasedTimeDelta]
    """Evalutes true when the step has been collecting valid throughput data for at least this long."""

    completed_at_least: Optional[OperationCount]
    """Evaluates true when at least this many operations have completed while the step was collecting valid throughput data."""

    average_duration_more_than: Optional[OperationLatency]
    """Evaluates true when the average duration of operations completed during the step exceeds the specified value."""

    throughput_stability_took_longer_than: Optional[StringBasedTimeDelta]
    """Evaluates true when reaching throughput stability took longer than this amount of time since the start of the step."""


class ThroughputPastPeak(ImplicitDict):
    operations: list[OperationType]
    """Operations for which throughput should be calculated."""

    fraction_of_peak: float
    """Trigger this threshold when throughput drops below this fraction of the peak throughput measured for any past step. [0, 1]"""


class LoadCompletionCriteria(ImplicitDict):
    """Completion criteria for an entire load.

    Any specified field that evaluates to false will cause this criterion to evaluate to false."""

    any_of: Optional[list[LoadCompletionCriteria]]

    throughput_lower_than_peak: Optional[ThroughputPastPeak]
    """Evaluates true when the throughput of the specified operations for the most recently-completed step drops below the specified fraction of the maximum throughput of all prior steps."""

    failures_more_than: Optional[OperationCount]
    """Evaluates true when the number of failures for the specified operations exceeds the specified number."""

    most_recent_step: Optional[StepCompletionCriteria]
    """Evaluates true when the most recently completed step meets these criteria."""


class UserRampLoad(ImplicitDict):
    """Ramps up users of a specified type, observing resulting throughput."""

    user_type: BenchmarkUserName
    """Type of user to instantiate."""

    initial_users: int = 1
    """Number of users to start with."""

    additional_users_per_step: int = 1
    """Additional users to add at each step along the ramp."""

    throughput_stability_criteria: ThroughputStabilityCriteria
    """Throughput of the current step is considered stable once these criteria are met."""

    step_completion_criteria: StepCompletionCriteria
    """The current step is considered complete once these criteria are met."""

    load_completion_criteria: LoadCompletionCriteria
    """The load is considered complete if these criteria are met."""


class BenchmarkLoadSpecification(ImplicitDict):
    """Specification of how load will be applied."""

    name: BenchmarkLoadName

    user_ramp: Optional[UserRampLoad]
    """Load will be provided by ramping up the number of virtual users of a particular type/behavior."""
