from typing import Optional

from implicitdict import ImplicitDict

from monitoring.benchmarker.configurations.actions.f3411 import F3411ActionSpecification
from monitoring.benchmarker.configurations.actions.f3548 import F3548ActionSpecification
from monitoring.benchmarker.configurations.artifacts.artifact import (
    ArtifactSpecification,
)
from monitoring.monitorlib.expressions.types import ASTExpression


class BenchmarkActionName(str):
    """Unique (within benchmark configuration) name for an action to perform, for instance at setup and/or teardown of one or more scenarios."""

    pass


class RunCommandActionSpecification(ImplicitDict):
    """Shell command to run as a benchmark action."""

    command: str
    """Shell command to run."""

    path: str
    """Working folder in which to run the command.  `$REPO_ROOT` will be replaced with the root folder of the repo."""

    env: dict[str, str]
    """Override each environment variable key with the specified value before running the command."""


class GenerateArtifactsActionSpecification(ImplicitDict):
    """Generate an intermediate artifact (prior to final artifact generation) during benchmarker execution."""

    subfolder: Optional[ASTExpression]
    """If specified, place artifacts in a subfolder (relative to where normal artifacts will be generated) of this name.
    
    If not specified, artifacts will be generated in the same location as the normal artifacts (and may be overwritten).
    The variable `action_invocation` will be a 0-based integer indicating the index of the invocation of this action
    and will be available during the evaluation of this expression."""

    custom_artifacts: Optional[list[ArtifactSpecification]]
    """Generate these custom artifacts when this action is run."""

    defined_artifact_indices: Optional[list[int]]
    """Generate the artifacts from the main configuration having the indices listed here when this action is run."""


class BenchmarkActionSpecification(ImplicitDict):
    name: BenchmarkActionName

    run_command: Optional[RunCommandActionSpecification]

    f3411: Optional[F3411ActionSpecification]

    f3548: Optional[F3548ActionSpecification]

    generate_artifacts: Optional[GenerateArtifactsActionSpecification]
