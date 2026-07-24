from typing import Optional

from implicitdict import ImplicitDict

from monitoring.benchmarker.configurations.actions import (
    BenchmarkActionSpecification,
)
from monitoring.benchmarker.configurations.artifacts.artifact import (
    ArtifactSpecification,
)
from monitoring.benchmarker.configurations.loads import BenchmarkLoadSpecification
from monitoring.benchmarker.configurations.scenarios import (
    BenchmarkScenarioSpecification,
)
from monitoring.benchmarker.configurations.users import BenchmarkUserSpecification
from monitoring.uss_qualifier.resources.definitions import ResourceCollection


class BenchmarkConfiguration(ImplicitDict):
    resources: Optional[ResourceCollection]
    """Pool of uss_qualifier resources available for use by other resources in this benchmark configuration."""

    actions: Optional[list[BenchmarkActionSpecification]]
    """Actions available to be performed during the benchmarker run."""

    user_types: list[BenchmarkUserSpecification]
    """Types of users available to load the system under test during the benchmarker run."""

    loads: list[BenchmarkLoadSpecification]
    """Loads that can be applied to the system under test during the benchmarker run."""

    scenarios: list[BenchmarkScenarioSpecification]
    """The sequential list of scenarios to perform in the benchmarker run."""

    artifacts: Optional[list[ArtifactSpecification]]
    """Artifacts to produce from the data collected during the benchmarker run."""
