import os

from monitoring.benchmarker.artifacts.matplotlib.matplotlib_figure import (
    generate_matplotlib_figure,
)
from monitoring.benchmarker.artifacts.raw_report import generate_raw_report
from monitoring.benchmarker.configurations.artifacts.artifact import (
    ArtifactSpecification,
)
from monitoring.benchmarker.reports.report import BenchmarkRunReport


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
