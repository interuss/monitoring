from monitoring.benchmarker.configurations.actions import (
    BenchmarkActionName,
    BenchmarkActionSpecification,
)
from monitoring.benchmarker.engine.actions.run_command import run_command


def run_scenario_actions(
    action_names: list[BenchmarkActionName] | None,
    action_specs: dict[BenchmarkActionName, BenchmarkActionSpecification],
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

        if "run_command" in action_spec and action_spec.run_command is not None:
            run_command(action_spec.run_command)
        else:
            raise NotImplementedError(
                f"Action '{action_name}' has no recognized action specification implemented in this version of benchmarker"
            )
