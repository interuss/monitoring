from enum import StrEnum
from typing import Optional

from implicitdict import ImplicitDict

from monitoring.monitorlib.expressions.types import ASTExpression, SymbolExpression


class AxisSpecification(ImplicitDict):
    label: Optional[str]


class XYPlotType(StrEnum):
    Scatter = "Scatter"


class XYPlotSpecification(ImplicitDict):
    """Specification for a plot (artist) to show on a matplotlib Axes.

    When evaluating expressions, the BenchmarkRunReport will be available as the `report` symbol."""

    type: XYPlotType

    evaluation_context: Optional[list[SymbolExpression]]
    """Symbols available to other expressions in this plot specification."""

    x_data_expr: Optional[ASTExpression]
    """List of X data values for XY points.
    
    Must have the same number of entries as y_data.
    Defaults to 1, 2, 3, ..., N for N y_data values."""

    y_data_expr: ASTExpression
    """List of Y data values for XY points."""

    render_expr: Optional[ASTExpression]
    """If specified, whether this plot should be rendered (boolean).  Default true."""


class SubplotSpecification(ImplicitDict):
    title: Optional[str]

    evaluation_context: Optional[list[SymbolExpression]]
    """Symbols available to other expressions in this subplot specification."""

    x_axis: Optional[AxisSpecification]
    y_axis: Optional[AxisSpecification]
    xy_plots: list[XYPlotSpecification]


class SubfigureSpecification(ImplicitDict):
    title: Optional[str]

    n_subplot_rows: int = 1
    n_subplot_cols: int = 1

    evaluation_context: Optional[list[SymbolExpression]]
    """Symbols available to other expressions in this subfigure specification."""

    subplots: list[SubplotSpecification]


class MatplotlibFigureSpecification(ImplicitDict):
    name: str
    """Machine-level name for this figure.  Used as the output file name."""

    n_subfigure_rows: int = 1
    n_subfigure_cols: int = 1

    evaluation_context: Optional[list[SymbolExpression]]
    """Symbols available to other expressions in this figure specification."""

    subfigures: list[SubfigureSpecification]
