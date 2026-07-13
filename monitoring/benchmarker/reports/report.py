from typing import Optional

from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.benchmarker.configurations.configuration import BenchmarkConfiguration
from monitoring.benchmarker.configurations.loads import OperationType
from monitoring.monitorlib.fetch import Query


class BenchmarkOperation(ImplicitDict):
    """Record of an operation of a known type, origin, and outcome executed during a benchmark."""

    t0: StringBasedDateTime
    """Time this operation was started/initiated."""

    t1: StringBasedDateTime
    """Time this operation completed, either successsfully or in failure."""

    query: Optional[Query]
    """The query details for this operation, if this was a query operation and query details are being recorded."""


class OperationsByOutcome(ImplicitDict):
    """Record of operations grouped by whether they were successful."""

    successful: Optional[list[BenchmarkOperation]]
    """Operations that were successful (yielded successful user journeys)."""

    unsuccessful: Optional[list[BenchmarkOperation]]
    """Operations that were unsuccessful (did not yield successful user journeys due to errors, timeouts, aborts, etc)"""


class OperationsByOrigin(ImplicitDict):
    """Record of operations from a particular origin."""

    origin: str
    """Source/originator of the operations in this record; e.g., the user that initiated these operations."""

    outcomes: list[OperationsByOutcome]
    """Operations originating from this origin."""


class OperationsByType(ImplicitDict):
    """Record of operations of a particular type."""

    type: OperationType
    """The type of the operations in this record."""

    origins: list[OperationsByOrigin]
    """Operations of this particular type."""


class BenchmarkScenarioStepReport(ImplicitDict):
    load_factor: float
    """Load factor (e.g., number of users) present during this step."""

    start_time: StringBasedDateTime
    """Time this step started."""

    throughput_stability_time: StringBasedDateTime
    """Time during this step at which activity became sufficiently stable for throughput measurement."""

    end_time: StringBasedDateTime
    """Time this step ended."""


class BenchmarkScenarioReport(ImplicitDict):
    operations: list[OperationsByType]
    """All operations that occurred during the benchmark run."""

    steps: list[BenchmarkScenarioStepReport]
    """Boundaries of steps within this scenario."""

    metadata: dict = {}
    """Arbitrary metadata copied from the scenario specification."""


class BenchmarkReport(ImplicitDict):
    scenarios: list[BenchmarkScenarioReport]
    """Results of scenarios, corresponding to the scenarios defined in the configuration."""


class BenchmarkRunReport(ImplicitDict):
    codebase_version: str
    """Version of codebase used to run benchmarker."""

    commit_hash: str
    """Full commit hash of codebase used to run benchmarker."""

    configuration: BenchmarkConfiguration
    """Configuration used to run benchmarker."""

    report: BenchmarkReport
    """Report produced by benchmarker during this run."""
