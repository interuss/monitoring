import asyncio
from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from monitoring.benchmarker.configurations.configuration import BenchmarkConfiguration
from monitoring.benchmarker.engine.actions.actions import run_scenario_actions
from monitoring.benchmarker.engine.loads.loads import run_scenario_load
from monitoring.benchmarker.engine.operations import (
    group_operations,
)
from monitoring.benchmarker.engine.resources import instantiate_resources
from monitoring.benchmarker.reports.report import (
    BenchmarkReport,
    BenchmarkRunReport,
    BenchmarkScenarioReport,
)
from monitoring.monitorlib.versioning import get_code_version, get_commit_hash


async def _run_benchmark_async(
    config: BenchmarkConfiguration,
    codebase_version: str,
    commit_hash: str,
) -> BenchmarkRunReport:
    logger.info("Instantiating declared resources...")
    resource_pool = instantiate_resources(config)

    user_specs_map = {u.name: u for u in config.user_types}
    loads_map = {load.name: load for load in config.loads}

    max_io_threads = 400
    executor = ThreadPoolExecutor(
        max_workers=max_io_threads, thread_name_prefix="benchmarker_io_"
    )

    scenarios_reports: list[BenchmarkScenarioReport] = []

    action_list = config.actions if "actions" in config and config.actions else []
    action_specs = {action_spec.name: action_spec for action_spec in action_list}

    try:
        for scenario_spec in config.scenarios:
            logger.info(
                f"========== Starting Scenario '{scenario_spec.name}' =========="
            )

            # Run setup actions
            setup_actions = scenario_spec.setup if "setup" in scenario_spec else None
            run_scenario_actions(setup_actions, action_specs)

            # Run load
            if scenario_spec.load not in loads_map:
                raise ValueError(
                    f"Scenario load '{scenario_spec.load}' not defined in configuration.loads"
                )
            load_spec = loads_map[scenario_spec.load]
            scenario_ops, scenario_steps = await run_scenario_load(
                load_spec,
                user_specs_map,
                resource_pool,
                executor,
            )

            # Run teardown actions
            teardown_actions = (
                scenario_spec.teardown if "teardown" in scenario_spec else None
            )
            run_scenario_actions(teardown_actions, action_specs)

            # Generate and record scenario report
            scenario_report = BenchmarkScenarioReport(
                operations=group_operations(scenario_ops),
                steps=scenario_steps,
            )
            if "metadata" in scenario_spec:
                scenario_report.metadata = (
                    dict(scenario_spec.metadata)
                    if scenario_spec.metadata is not None
                    else None
                )
            scenarios_reports.append(scenario_report)

            logger.info(
                f"========== Completed Scenario '{scenario_spec.name}' =========="
            )
    finally:
        executor.shutdown(wait=True)

    run_report = BenchmarkRunReport(
        codebase_version=codebase_version,
        commit_hash=commit_hash,
        configuration=config,
        report=BenchmarkReport(scenarios=scenarios_reports),
    )

    return run_report


def run_benchmark(config: BenchmarkConfiguration) -> BenchmarkRunReport:
    """Execute the benchmarker engine for the provided configuration and return the resulting report."""
    codebase_version = get_code_version()
    commit_hash = get_commit_hash()
    return asyncio.run(_run_benchmark_async(config, codebase_version, commit_hash))
