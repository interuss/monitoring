from typing import Optional

from implicitdict import ImplicitDict


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


class BenchmarkActionSpecification(ImplicitDict):
    name: BenchmarkActionName

    run_command: Optional[RunCommandActionSpecification]
