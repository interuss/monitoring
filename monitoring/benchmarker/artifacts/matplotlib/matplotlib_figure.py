import os

import matplotlib
from loguru import logger

matplotlib.use("Agg")  # Non-interactive backend suitable for headless benchmarking
import matplotlib.pyplot as plt

from monitoring.benchmarker.configurations.artifacts.matplotlib_figure import (
    MatplotlibFigureSpecification,
)
from monitoring.benchmarker.reports.report import BenchmarkRunReport


def generate_matplotlib_figure(
    report: BenchmarkRunReport, fig_spec: MatplotlibFigureSpecification, output_dir: str
) -> None:
    filename = (
        fig_spec.name
        if fig_spec.name.lower().endswith(".png")
        else f"{fig_spec.name}.png"
    )
    out_path = os.path.join(output_dir, filename)
    logger.info(
        f"Generating Matplotlib figure artifact '{fig_spec.name}' -> {out_path}"
    )

    fig = plt.figure(
        figsize=(8 * fig_spec.n_subfigure_cols, 5 * fig_spec.n_subfigure_rows)
    )

    # TODO: Populate graph

    plt.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
