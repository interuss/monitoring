from typing import Optional

from implicitdict import ImplicitDict

from monitoring.benchmarker.configurations.actions import BenchmarkActionName
from monitoring.benchmarker.configurations.loads import BenchmarkLoadName


class BenchmarkScenarioName(str):
    """Unique (within benchmark configuration) name for a scenario."""

    pass


class BenchmarkScenarioSpecification(ImplicitDict):
    name: BenchmarkScenarioName

    setup: Optional[list[BenchmarkActionName]]
    """Actions to perform before beginning load testing in this scenario."""

    load: BenchmarkLoadName
    """How and when to generate load in this scenario."""

    teardown: Optional[list[BenchmarkActionName]]
    """Actions to perform after completing load testing in this scenario."""

    record_query_details: bool = False
    """When true, include full details in the report for queries made during this scenario."""

    metadata: dict
    """Arbitrary data that may be relevant to the scenario."""
