import os

from asteval import Interpreter
from loguru import logger

from monitoring.benchmarker.artifacts.generation import generate_artifacts
from monitoring.benchmarker.configurations.actions.action import (
    BenchmarkActionName,
    GenerateArtifactsActionSpecification,
)
from monitoring.benchmarker.configurations.artifacts.artifact import (
    ArtifactSpecification,
)
from monitoring.benchmarker.configurations.configuration import BenchmarkConfiguration
from monitoring.benchmarker.reports.report import (
    BenchmarkReport,
    BenchmarkRunReport,
    BenchmarkScenarioReport,
)
from monitoring.monitorlib.expressions.evaluation import evaluate_expression


def generate_intermediate_artifacts(
    gen_spec: GenerateArtifactsActionSpecification,
    action_name: BenchmarkActionName,
    invocation: int,
    config: BenchmarkConfiguration,
    scenarios_reports: list[BenchmarkScenarioReport],
    output_dir: str,
    codebase_version: str,
    commit_hash: str,
) -> None:
    target_dir = output_dir
    if "subfolder" in gen_spec and gen_spec.subfolder is not None:
        interpreter = Interpreter(user_symbols={"action_invocation": invocation})
        subfolder_val = evaluate_expression(
            gen_spec.subfolder, f"action.{action_name}.subfolder", interpreter
        )
        if subfolder_val is not None and str(subfolder_val).strip():
            target_dir = os.path.join(output_dir, str(subfolder_val))

    artifacts_to_generate: list[ArtifactSpecification] = []
    if "custom_artifacts" in gen_spec and gen_spec.custom_artifacts:
        artifacts_to_generate.extend(gen_spec.custom_artifacts)

    if "defined_artifact_indices" in gen_spec and gen_spec.defined_artifact_indices:
        if "artifacts" not in config or not config.artifacts:
            raise ValueError(
                f"Action '{action_name}' specifies defined_artifact_indices, but no artifacts are defined in the main configuration"
            )
        for idx in gen_spec.defined_artifact_indices:
            if idx < 0 or idx >= len(config.artifacts):
                raise ValueError(
                    f"Action '{action_name}' references defined_artifact_indices [{idx}], which is out of range (configuration defined {len(config.artifacts)} artifacts)"
                )
            artifacts_to_generate.append(config.artifacts[idx])

    if not artifacts_to_generate:
        logger.warning(
            f"Action '{action_name}' generate_artifacts specified no artifacts to generate"
        )
        return

    logger.info(
        f"Action '{action_name}' (invocation {invocation}): generating {len(artifacts_to_generate)} artifact(s) in {target_dir}"
    )

    current_report = BenchmarkRunReport(
        codebase_version=codebase_version,
        commit_hash=commit_hash,
        configuration=config,
        report=BenchmarkReport(scenarios=list(scenarios_reports)),
    )

    generate_artifacts(artifacts_to_generate, current_report, target_dir)
