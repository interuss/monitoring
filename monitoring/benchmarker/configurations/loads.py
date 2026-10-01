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

    FlightPlannerActiveFlight = "flight_planner.active_flight"
    """An operation involving only active flight time from the time the operator starts using the airspace until the time the operator finishes using the airspace."""


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
    """Criteria used to determine when it is valid to start collecting throughput data in a step
    (throughput is stable), or whether there is too much load to collect valid throughput data
    (throughput is unstable).

    Any specified field that evaluates to false will cause this criteria to evaluate to false."""

    any_of: Optional[list[ThroughputStabilityCriteria]]

    each_user_completed_at_least: Optional[OperationCount]
    """Evaluates true when each user has completed at least this many operations in the step's current phase."""

    phase_duration_at_least: Optional[StringBasedTimeDelta]
    """Evaluates true when the step has been in its current phase for at least this long."""

    average_duration_more_than: Optional[OperationLatency]
    """Evaluates true when the average duration of operations completed in the step's current phase exceeds the specified value."""

    failures_more_than: Optional[OperationCount]
    """Evaluates true when the number of failures for the specified operations exceeds the specified number in the step's current phase."""


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
    """Evaluates true when the step has been collecting valid throughput data for at least this long."""

    completed_at_least: Optional[OperationCount]
    """Evaluates true when at least this many operations have completed while the step was collecting valid throughput data."""

    average_duration_more_than: Optional[OperationLatency]
    """Evaluates true when the average duration of operations completed during the step exceeds the specified value."""

    throughput_stability_took_longer_than: Optional[StringBasedTimeDelta]
    """Evaluates true when reaching throughput stability took longer than this amount of time since the start of the step."""

    failures_more_than: Optional[OperationCount]
    """Evaluates true when the number of failures for the specified operations exceeds the specified number during this step."""


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

    completed_steps: Optional[int]
    """Evaluates true when this many steps have been completed."""

    most_recent_step: Optional[StepCompletionCriteria]
    """Evaluates true when the most recently completed step meets these criteria."""


class UserBasedLoad(ImplicitDict):
    user_type: Optional[BenchmarkUserName]
    """Type of user to instantiate."""

    user_types: Optional[list[BenchmarkUserName]]
    """Types of users to instantiate, cycling through them in order as load increases."""

    throughput_stability_criteria: ThroughputStabilityCriteria
    """Throughput of the current step is considered stable once these criteria are met."""

    throughput_instability_criteria: Optional[ThroughputStabilityCriteria]
    """If these criteria are met, throughput is considered to be unstable and step will not continue."""

    step_completion_criteria: StepCompletionCriteria
    """The current step is considered complete once these criteria are met."""


class UserRampLoad(UserBasedLoad):
    """Ramps up users of specified type(s), observing resulting throughput."""

    initial_users: int = 1
    """Number of users to start with."""

    additional_users_per_step: int = 1
    """Additional users to add at each step along the ramp."""

    load_completion_criteria: LoadCompletionCriteria
    """The load is considered complete if these criteria are met."""

    random_seed: Optional[int]
    """Seed to use to randomly generate seeds for each user."""


class SearchCompletionCriteria(ImplicitDict):
    """Completion criteria for a user-count search.

    Any specified field that evaluates to false will cause this criteria object to evaluate to false."""

    any_of: Optional[list[SearchCompletionCriteria]]

    adjacency_user_count: Optional[int]
    """Number of users between steps considered 'consecutive' or 'adjacent'.  Defaults to 1 when unspecified.
    
    For instance, adjacency_user_count of 3 means that a step with 7 users and a step with 10 users are adjacent (or consecutive), but a step with 12 users and a step with 16 users are not adjacent (or consecutive)."""

    consecutive_unstable_user_counts: Optional[int]
    """There are at least this many consecutive user-count steps which ended in instability, preceded immediately by a step with stability.
     
    For instance, 24 users produced instability as well as 25 users and 26 users, but 23 users completed the step successfully."""

    consecutive_stable_user_counts: Optional[int]
    """There are at least this many consecutive user-count steps which completed successfully, followed immediately by a step with instability.
     
    For instance, the 21-users step completed successfully, as did 22 users and 23 users, but 24 users produced instability."""

    maximum_left_side_spacing: Optional[float]
    """No two user-count steps lower than the user-count step with the maximum measured throughput may be further apart than this fraction of the user-count of that maximum-throughput step.
    
    For instance, with max throughput at 90 users and maximum_left_side_spacing=0.1, the user-count spacing between two adjacent steps with fewer than 90 users may not exceed 9 users.
    So, if there were no steps between 20 users and 32 users, an additional step would need to be measured between 21 and 31 users."""

    max_throughput_adjacent_user_counts: Optional[int]
    """The user-count step with the maximum throughput must have at least this many consecutive adjacent user-count steps unless/until an unstable step is encountered.
    
    For instance, if maximum throughput was detected at 56 users and max_throughput_adjacent_user_counts were 3, then steps with user counts of 53, 54, 55, 57, 58, and 59 must be measured normally.
    However, if the step with 57 users were unstable, then the steps with 58 and 59 users would not need to be measured."""


class UserSearchLoad(UserBasedLoad):
    """Searches through quantities of users to find the point where throughput becomes unstable."""

    initial_users: int = 1
    """Number of users to start with."""

    user_expansion_ratio: float = 2
    """When more users are needed than have been used in any previous step, expand the largest previous number of users by this fraction (or 1 user, whichever is larger)."""

    search_completion_criteria: SearchCompletionCriteria
    """The search is considered complete if these criteria are met."""

    random_seed: Optional[int]
    """Seed to use to randomly generate seeds for each user."""


class BenchmarkLoadSpecification(ImplicitDict):
    """Specification of how load will be applied."""

    name: BenchmarkLoadName

    user_ramp: Optional[UserRampLoad]
    """Load will be provided by ramping up the number of virtual users of a particular type/behavior."""

    user_search: Optional[UserSearchLoad]
    """Load will be provided by adaptively adjusting the number of virtual users of a particular type/behavior until desired characteristics of the throughput curve are discovered."""
