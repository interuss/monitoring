import os

from monitoring.benchmarker.artifacts.matplotlib.matplotlib_figure import (
    generate_matplotlib_figure,
)
from monitoring.benchmarker.artifacts.raw_report import generate_raw_report
from monitoring.benchmarker.artifacts.timeline.timeline import generate_timeline
from monitoring.benchmarker.configurations.artifacts.artifact import (
    ArtifactSpecification,
)
from monitoring.benchmarker.reports.report import BenchmarkRunReport


def default_output_path(config_name: str) -> str:
    """Determine default output directory for a given configuration name.

    Args:
        config_name: Configuration string or file reference (e.g. file://path/to/config.jsonnet)

    Returns: Path to output directory under output/<name of config>
    """
    if any(
        config_name.lower().endswith(ext)
        for ext in (
            ".jsonnet",
            ".json",
            ".yaml",
            ".yml",
            ".kml",
        )
    ):
        simple_config_name = os.path.splitext(config_name)[0]
    else:
        simple_config_name = config_name
    simple_config_name = simple_config_name.split(".")[-1]
    simple_config_name = os.path.split(simple_config_name)[-1]

    benchmarker_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(benchmarker_dir, "output", simple_config_name)


def generate_artifacts(
    artifacts_specs: list[ArtifactSpecification],
    report: BenchmarkRunReport,
    output_dir: str,
) -> None:
    """Generate and save all configured artifacts."""
    os.makedirs(output_dir, exist_ok=True)

    for spec in artifacts_specs:
        if "raw_report" in spec and spec.raw_report is not None:
            generate_raw_report(report, spec.raw_report, output_dir)

        if "matplotlib_figure" in spec and spec.matplotlib_figure is not None:
            generate_matplotlib_figure(report, spec.matplotlib_figure, output_dir)

        if "timeline" in spec and spec.timeline is not None:
            generate_timeline(report, spec.timeline, output_dir)

