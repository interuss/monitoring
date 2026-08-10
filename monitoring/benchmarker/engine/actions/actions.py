from monitoring.benchmarker.configurations.actions import (
    BenchmarkActionName,
    BenchmarkActionSpecification,
)
from monitoring.benchmarker.configurations.configuration import BenchmarkConfiguration
from monitoring.benchmarker.engine.actions.generate_artifacts import (
    generate_intermediate_artifacts,
)
from monitoring.benchmarker.engine.actions.run_command import run_command
from monitoring.benchmarker.reports.report import BenchmarkScenarioReport


def run_scenario_actions(
    action_names: list[BenchmarkActionName] | None,
    action_specs: dict[BenchmarkActionName, BenchmarkActionSpecification],
    action_invocations: dict[BenchmarkActionName, int],
    config: BenchmarkConfiguration,
    scenarios_reports: list[BenchmarkScenarioReport],
    output_dir: str,
    codebase_version: str,
    commit_hash: str,
) -> None:
    """Run a sequence of scenario setup or teardown actions by name."""
    if not action_names:
        return

    for action_name in action_names:
        if action_name not in action_specs:
            raise ValueError(
                f"Scenario action '{action_name}' not defined in configuration.actions"
            )
        action_spec = action_specs[action_name]
        invocation = action_invocations.get(action_name, 0)
        action_performed = False

        if "run_command" in action_spec and action_spec.run_command is not None:
            run_command(action_spec.run_command)
            action_performed = True
        if (
            "generate_artifacts" in action_spec
            and action_spec.generate_artifacts is not None
        ):
            generate_intermediate_artifacts(
                action_spec.generate_artifacts,
                action_name,
                invocation,
                config,
                scenarios_reports,
                output_dir,
                codebase_version,
                commit_hash,
            )
            action_performed = True

        if not action_performed:
            raise NotImplementedError(
                f"Action '{action_name}' has no recognized action specification implemented in this version of benchmarker"
            )

        action_invocations[action_name] = invocation + 1
