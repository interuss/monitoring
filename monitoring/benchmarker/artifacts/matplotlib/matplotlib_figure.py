import inspect
import os

import matplotlib
from loguru import logger

matplotlib.use("Agg")  # Non-interactive backend suitable for headless benchmarking
import matplotlib.pyplot as plt
import numpy as np

from monitoring.benchmarker.configurations.artifacts.matplotlib_figure import (
    MatplotlibFigureSpecification,
    XYPlotType,
)
from monitoring.benchmarker.reports import analysis
from monitoring.benchmarker.reports.report import BenchmarkRunReport
from monitoring.monitorlib.expressions.evaluation import (
    evaluate_expression,
    get_updated_context,
)


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
    subfigs_res = fig.subfigures(fig_spec.n_subfigure_rows, fig_spec.n_subfigure_cols)
    if isinstance(subfigs_res, np.ndarray):
        subfigs = list(subfigs_res.flatten())
    elif isinstance(subfigs_res, (list, tuple)):
        subfigs = list(subfigs_res)
    else:
        subfigs = [subfigs_res]

    analysis_functions = {
        name: obj for name, obj in inspect.getmembers(analysis, inspect.isfunction)
    }

    figure_symbols, _ = get_updated_context(
        {
            "report": report,
        }
        | analysis_functions,
        fig_spec.evaluation_context
        if "evaluation_context" in fig_spec and fig_spec.evaluation_context
        else [],
    )

    for idx, subfig_spec in enumerate(fig_spec.subfigures):
        if idx >= len(subfigs):
            raise ValueError(
                f"More subfigures defined than grid capacity ({len(subfigs)})"
            )

        subfig_symbols, _ = get_updated_context(
            figure_symbols,
            subfig_spec.evaluation_context
            if "evaluation_context" in subfig_spec and subfig_spec.evaluation_context
            else [],
        )

        subfig = subfigs[idx]
        if "title" in subfig_spec and subfig_spec.title:
            subfig.suptitle(subfig_spec.title)

        axes_res = subfig.subplots(
            subfig_spec.n_subplot_rows, subfig_spec.n_subplot_cols
        )
        if isinstance(axes_res, np.ndarray):
            axes = list(axes_res.flatten())
        elif isinstance(axes_res, (list, tuple)):
            axes = list(axes_res)
        else:
            axes = [axes_res]

        for s_idx, subplot_spec in enumerate(subfig_spec.subplots):
            if s_idx >= len(axes):
                raise ValueError(
                    f"More subplots defined than subfigure capacity ({len(axes)})"
                )

            subplot_symbols, _ = get_updated_context(
                subfig_symbols,
                subplot_spec.evaluation_context
                if "evaluation_context" in subplot_spec
                and subplot_spec.evaluation_context
                else [],
            )

            ax = axes[s_idx]
            if "title" in subplot_spec and subplot_spec.title:
                ax.set_title(subplot_spec.title)

            if "x_axis" in subplot_spec and subplot_spec.x_axis:
                if "label" in subplot_spec.x_axis and subplot_spec.x_axis.label:
                    ax.set_xlabel(subplot_spec.x_axis.label)

            if "y_axis" in subplot_spec and subplot_spec.y_axis:
                if "label" in subplot_spec.y_axis and subplot_spec.y_axis.label:
                    ax.set_ylabel(subplot_spec.y_axis.label)

            for xy_plot in subplot_spec.xy_plots:
                _, xyplot_interpreter = get_updated_context(
                    subplot_symbols,
                    xy_plot.evaluation_context
                    if "evaluation_context" in xy_plot and xy_plot.evaluation_context
                    else [],
                )

                if "render_expr" in xy_plot and xy_plot.render_expr is not None:
                    render = evaluate_expression(
                        xy_plot.render_expr, "render", xyplot_interpreter
                    )
                    if not render:
                        continue

                y_vals = evaluate_expression(
                    xy_plot.y_data_expr, "y_data_expr", xyplot_interpreter
                )
                if not isinstance(y_vals, (list, tuple, np.ndarray)):
                    raise ValueError(
                        f"y_data_expr '{xy_plot.y_data_expr}' evaluated to non-sequence type: {type(y_vals)}"
                    )

                if "x_data_expr" in xy_plot and xy_plot.x_data_expr is not None:
                    x_vals = evaluate_expression(
                        xy_plot.x_data_expr, "x_data_expr", xyplot_interpreter
                    )
                    if not isinstance(x_vals, (list, tuple, np.ndarray)):
                        raise ValueError(
                            f"x_data_expr '{xy_plot.x_data_expr}' evaluated to non-sequence type: {type(x_vals)}"
                        )
                else:
                    x_vals = list(range(1, len(y_vals) + 1))

                if xy_plot.type == XYPlotType.Scatter:
                    ax.scatter(x_vals, y_vals)
                else:
                    raise NotImplementedError(
                        f"XYPlotType '{xy_plot.type}' not implemented"
                    )

    plt.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
