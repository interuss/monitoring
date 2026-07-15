from concurrent.futures import ThreadPoolExecutor
from typing import Any

from monitoring.benchmarker.configurations.loads import (
    BenchmarkLoadSpecification,
)
from monitoring.benchmarker.configurations.users import (
    BenchmarkUserName,
    BenchmarkUserSpecification,
)
from monitoring.benchmarker.engine.loads.user_ramp.user_ramp import run_user_ramp_load
from monitoring.benchmarker.engine.operations import ExecutedOperation
from monitoring.benchmarker.reports.report import BenchmarkScenarioStepReport
from monitoring.uss_qualifier.resources.definitions import ResourceID


async def run_scenario_load(
    load_spec: BenchmarkLoadSpecification,
    user_specs_map: dict[BenchmarkUserName, BenchmarkUserSpecification],
    resource_pool: dict[ResourceID, Any],
    executor: ThreadPoolExecutor,
) -> tuple[list[ExecutedOperation], list[BenchmarkScenarioStepReport]]:
    """Execute a scenario load."""
    if "user_ramp" in load_spec and load_spec.user_ramp:
        return await run_user_ramp_load(
            load_spec.user_ramp,
            user_specs_map,
            resource_pool,
            executor,
        )
    else:
        raise NotImplementedError(
            f"Load specification '{load_spec.name}' does not specify any supported load type"
        )
