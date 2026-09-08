import inspect
import os
from typing import Any

import matplotlib
from loguru import logger
from matplotlib.axes import Axes

matplotlib.use("Agg")  # Non-interactive backend suitable for headless benchmarking
import matplotlib.pyplot as plt
import numpy as np

from monitoring.benchmarker.configurations.artifacts.matplotlib_figure import (
    AxisSpecification,
    MatplotlibFigureSpecification,
    XYPlotType,
)
from monitoring.benchmarker.reports import analysis
from monitoring.benchmarker.reports.report import BenchmarkRunReport
from monitoring.monitorlib.expressions.evaluation import (
    evaluate_expression,
    get_updated_context,
)


def _extract_numbers(val) -> list[float]:
    if val is None:
        return []
    if isinstance(val, (int, float, np.number)):
        if not np.isnan(val):
            return [float(val)]
        return []
    if isinstance(val, (list, tuple, np.ndarray, set)):
        res = []
        for item in val:
            res.extend(_extract_numbers(item))
        return res
    try:
        return [float(val)]
    except (ValueError, TypeError):
        return []


def _configure_axis(
    ax_obj: Axes,
    axis_spec: AxisSpecification,
    is_x: bool,
    interpreter: Any,
    name_prefix: str,
) -> None:
    if "label" in axis_spec and axis_spec.label:
        if is_x:
            ax_obj.set_xlabel(axis_spec.label)
        else:
            ax_obj.set_ylabel(axis_spec.label)

    if "margin" in axis_spec and axis_spec.margin is not None:
        if is_x:
            ax_obj.margins(x=axis_spec.margin)
        else:
            ax_obj.margins(y=axis_spec.margin)

    min_val = None
    if "min_value" in axis_spec and axis_spec.min_value is not None:
        min_val = axis_spec.min_value
    if "min_value_expr" in axis_spec and axis_spec.min_value_expr is not None:
        val = evaluate_expression(
            axis_spec.min_value_expr, f"{name_prefix}.min_value_expr", interpreter
        )
        nums = _extract_numbers(val)
        if nums:
            min_val = min(nums)

    max_val = None
    if "max_value" in axis_spec and axis_spec.max_value is not None:
        max_val = axis_spec.max_value
    if "max_value_expr" in axis_spec and axis_spec.max_value_expr is not None:
        val = evaluate_expression(
            axis_spec.max_value_expr, f"{name_prefix}.max_value_expr", interpreter
        )
        nums = _extract_numbers(val)
        if nums:
            max_val = max(nums)

    lim_kwargs: dict[str, Any] = {}
    if min_val is not None:
        lim_kwargs["left" if is_x else "bottom"] = min_val
    if max_val is not None:
        lim_kwargs["right" if is_x else "top"] = max_val
    if lim_kwargs:
        if is_x:
            ax_obj.set_xlim(**lim_kwargs)
        else:
            ax_obj.set_ylim(**lim_kwargs)


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

    max_sub_rows = max((s.n_subplot_rows for s in fig_spec.subfigures), default=1)
    max_sub_cols = max((s.n_subplot_cols for s in fig_spec.subfigures), default=1)
    fig_width = (
        fig_spec.width
        if "width" in fig_spec and fig_spec.width is not None
        else 8 * fig_spec.n_subfigure_cols * max_sub_cols
    )
    fig_height = (
        fig_spec.height
        if "height" in fig_spec and fig_spec.height is not None
        else 5 * fig_spec.n_subfigure_rows * max_sub_rows
    )

    fig = plt.figure(
        figsize=(fig_width, fig_height),
        layout="constrained",
    )

    engine = fig.get_layout_engine()
    if engine is not None:
        engine_kwargs: dict[str, Any] = {
            "w_pad": fig_spec.w_pad
            if "w_pad" in fig_spec and fig_spec.w_pad is not None
            else 0.08,
            "h_pad": fig_spec.h_pad
            if "h_pad" in fig_spec and fig_spec.h_pad is not None
            else 0.12,
        }
        if "wspace" in fig_spec and fig_spec.wspace is not None:
            engine_kwargs["wspace"] = fig_spec.wspace
        if "hspace" in fig_spec and fig_spec.hspace is not None:
            engine_kwargs["hspace"] = fig_spec.hspace
        engine.set(**engine_kwargs)

    if "title" in fig_spec and fig_spec.title:
        fig.suptitle(fig_spec.title)

    subfig_kwargs: dict[str, Any] = {}
    if "wspace" in fig_spec and fig_spec.wspace is not None:
        subfig_kwargs["wspace"] = fig_spec.wspace
    elif fig_spec.n_subfigure_cols > 1:
        subfig_kwargs["wspace"] = 0.08
    if "hspace" in fig_spec and fig_spec.hspace is not None:
        subfig_kwargs["hspace"] = fig_spec.hspace
    elif fig_spec.n_subfigure_rows > 1:
        subfig_kwargs["hspace"] = 0.08

    subfigs_res = fig.subfigures(
        fig_spec.n_subfigure_rows, fig_spec.n_subfigure_cols, **subfig_kwargs
    )
    if isinstance(subfigs_res, np.ndarray):
        subfigs = list(subfigs_res.flatten())
    elif isinstance(subfigs_res, (list, tuple)):
        subfigs = list(subfigs_res)
    else:
        subfigs = [subfigs_res]

    analysis_functions = {
        name: obj for name, obj in inspect.getmembers(analysis, inspect.isfunction)
    }
    analysis_classes = {
        name: obj for name, obj in inspect.getmembers(analysis, inspect.isclass)
    }

    figure_symbols, figure_interpreter = get_updated_context(
        {
            "report": report,
        }
        | analysis_functions
        | analysis_classes,
        fig_spec.evaluation_context
        if "evaluation_context" in fig_spec and fig_spec.evaluation_context
        else [],
    )

    for idx, subfig_spec in enumerate(fig_spec.subfigures):
        if idx >= len(subfigs):
            raise ValueError(
                f"More subfigures defined than grid capacity ({len(subfigs)})"
            )

        if "render_expr" in subfig_spec and subfig_spec.render_expr:
            render = evaluate_expression(
                subfig_spec.render_expr, "render_expr", figure_interpreter
            )
            if not render:
                continue

        subfig_symbols, subfig_interpreter = get_updated_context(
            figure_symbols,
            subfig_spec.evaluation_context
            if "evaluation_context" in subfig_spec and subfig_spec.evaluation_context
            else [],
        )

        subfig = subfigs[idx]
        if "title" in subfig_spec and subfig_spec.title:
            subfig.suptitle(subfig_spec.title)

        gridspec_kw: dict[str, Any] = {}
        if "wspace" in subfig_spec and subfig_spec.wspace is not None:
            gridspec_kw["wspace"] = subfig_spec.wspace
        if "hspace" in subfig_spec and subfig_spec.hspace is not None:
            gridspec_kw["hspace"] = subfig_spec.hspace

        axes_res = subfig.subplots(
            subfig_spec.n_subplot_rows,
            subfig_spec.n_subplot_cols,
            gridspec_kw=gridspec_kw if gridspec_kw else None,
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

            if "render_expr" in subplot_spec and subplot_spec.render_expr:
                render = evaluate_expression(
                    subplot_spec.render_expr, "render_expr", subfig_interpreter
                )
                if not render:
                    continue

            subplot_symbols, subplot_interpreter = get_updated_context(
                subfig_symbols,
                subplot_spec.evaluation_context
                if "evaluation_context" in subplot_spec
                and subplot_spec.evaluation_context
                else [],
            )

            ax: Axes = axes[s_idx]
            subplot_y_axes: list[Axes] = [ax]
            if "title" in subplot_spec and subplot_spec.title:
                ax.set_title(subplot_spec.title)

            if "y_axes" in subplot_spec and subplot_spec.y_axes:
                for i in range(len(subplot_spec.y_axes)):
                    sec_ax = ax.twinx()
                    if i >= 1:
                        sec_ax.spines["right"].set_position(("outward", 60 * i))
                    subplot_y_axes.append(sec_ax)

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

                label = None
                if "label_expr" in xy_plot and xy_plot.label_expr is not None:
                    label_val = evaluate_expression(
                        xy_plot.label_expr, "label_expr", xyplot_interpreter
                    )
                    if label_val is not None:
                        label = str(label_val)

                kwargs: dict[str, Any] = {"label": label}
                if "color" in xy_plot and xy_plot.color:
                    kwargs["color"] = xy_plot.color
                if "kwargs" in xy_plot and xy_plot.kwargs:
                    kwargs = kwargs | xy_plot.kwargs

                y_axis_idx = 0
                if "y_axis" in xy_plot and xy_plot.y_axis is not None:
                    y_axis_idx = xy_plot.y_axis
                while len(subplot_y_axes) <= y_axis_idx:
                    sec_ax = ax.twinx()
                    offset_idx = len(subplot_y_axes) - 1
                    if offset_idx >= 1:
                        sec_ax.spines["right"].set_position(
                            ("outward", 60 * offset_idx)
                        )
                    subplot_y_axes.append(sec_ax)
                target_ax = subplot_y_axes[y_axis_idx]

                if xy_plot.type == XYPlotType.Scatter:
                    target_ax.scatter(x_vals, y_vals, **kwargs)
                elif xy_plot.type == XYPlotType.Line:
                    target_ax.plot(x_vals, y_vals, **kwargs)
                else:
                    raise NotImplementedError(
                        f"XYPlotType '{xy_plot.type}' not implemented"
                    )

            if "x_axis" in subplot_spec and subplot_spec.x_axis:
                _configure_axis(
                    ax, subplot_spec.x_axis, True, subplot_interpreter, "x_axis"
                )

            if "y_axis" in subplot_spec and subplot_spec.y_axis:
                _configure_axis(
                    subplot_y_axes[0],
                    subplot_spec.y_axis,
                    False,
                    subplot_interpreter,
                    "y_axis",
                )

            if "y_axes" in subplot_spec and subplot_spec.y_axes:
                for i, sec_y_spec in enumerate(subplot_spec.y_axes):
                    _configure_axis(
                        subplot_y_axes[i + 1],
                        sec_y_spec,
                        False,
                        subplot_interpreter,
                        f"y_axes[{i}]",
                    )

            if "legend" in subplot_spec and subplot_spec.legend:
                legend_spec = subplot_spec.legend
                legend_kwargs: dict[str, Any] = {}
                if "location" in legend_spec and legend_spec.location:
                    legend_kwargs["loc"] = str(legend_spec.location)
                if "font_size" in legend_spec and legend_spec.font_size:
                    legend_kwargs["fontsize"] = str(legend_spec.font_size)
                if (
                    "label_spacing" in legend_spec
                    and legend_spec.label_spacing is not None
                ):
                    legend_kwargs["labelspacing"] = float(legend_spec.label_spacing)
                if (
                    "border_padding" in legend_spec
                    and legend_spec.border_padding is not None
                ):
                    legend_kwargs["borderpad"] = float(legend_spec.border_padding)
                handles = []
                labels = []
                for y_ax in subplot_y_axes:
                    ax_handles, ax_labels = y_ax.get_legend_handles_labels()
                    handles.extend(ax_handles)
                    labels.extend(ax_labels)
                if handles:
                    subplot_y_axes[-1].legend(handles, labels, **legend_kwargs)
                else:
                    subplot_y_axes[-1].legend(**legend_kwargs)

    save_kwargs: dict[str, Any] = {"bbox_inches": "tight"}
    if "dpi" in fig_spec and fig_spec.dpi is not None:
        save_kwargs["dpi"] = fig_spec.dpi
    fig.savefig(out_path, **save_kwargs)
    plt.close(fig)
