from enum import StrEnum
from typing import Optional

from implicitdict import ImplicitDict

from monitoring.monitorlib.expressions.types import ASTExpression, SymbolExpression


class AxisSpecification(ImplicitDict):
    label: Optional[str]

    min_value: Optional[float]
    """If specified, the minimum value of this axis."""

    min_value_expr: Optional[ASTExpression]
    """If specified, an expression for the minimum value of this axis.
    
    Takes precedence over min_value."""

    max_value: Optional[float]
    """If specified, the maximum value of this axis."""

    max_value_expr: Optional[ASTExpression]
    """If specified, an expression for the maximum value of this axis.
    
    Takes precedence over max_value."""


class XYPlotType(StrEnum):
    Scatter = "Scatter"
    Line = "Line"


class XYPlotSpecification(ImplicitDict):
    """Specification for a plot (artist) to show on a matplotlib Axes.

    When evaluating expressions, the BenchmarkRunReport will be available as the `report` symbol."""

    type: XYPlotType

    label_expr: Optional[ASTExpression]
    """Expression for the label of this plot/artist (string), primarily used in the plot legend."""

    color: Optional[str]
    """Matplotlib color string for this plot.
    
    See https://matplotlib.org/stable/users/explain/colors/colors.html#colors-def"""

    evaluation_context: Optional[list[SymbolExpression]]
    """Symbols available to other expressions in this plot specification."""

    x_data_expr: Optional[ASTExpression]
    """List of X data values for XY points.
    
    Must have the same number of entries as y_data.
    Defaults to 1, 2, 3, ..., N for N y_data values."""

    y_data_expr: ASTExpression
    """List of Y data values for XY points."""

    y_axis: Optional[int]
    """Which Y axis to associate this data with.
    
    0 is the primary Y axis (default), 1 is secondary Y axis, 2 is tertiary, etc.
    Additional axes are created <primary axes>.twinx()."""

    render_expr: Optional[ASTExpression]
    """If specified, whether this plot should be rendered (boolean).  Default true."""

    kwargs: Optional[dict]
    """If specified, pass these additional keyword arguments to the plot function."""


class LegendLocation(StrEnum):
    Best = "best"
    UpperRight = "upper right"
    UpperLeft = "upper left"
    LowerLeft = "lower left"
    LowerRight = "lower right"
    Right = "right"
    CenterLeft = "center left"
    CenterRight = "center right"
    LowerCenter = "lower center"
    UpperCenter = "upper center"
    Center = "center"


class LegendFontSize(StrEnum):
    XXSmall = "xx-small"
    XSmall = "x-small"
    Small = "small"
    Medium = "medium"
    Large = "large"
    XLarge = "x-large"
    XXLarge = "xx-large"


class LegendSpecification(ImplicitDict):
    location: Optional[LegendLocation]

    font_size: Optional[LegendFontSize]

    label_spacing: Optional[float]
    """The vertical space between the legend entries, in font-size units."""

    border_padding: Optional[float]
    """The fractional whitespace inside the legend border, in font-size units."""


class SubplotSpecification(ImplicitDict):
    title: Optional[str]
    """Title of this subplot."""

    evaluation_context: Optional[list[SymbolExpression]]
    """Symbols available to other expressions in this subplot specification."""

    x_axis: Optional[AxisSpecification]
    """Characteristics of the X axis of this subplot."""

    y_axis: Optional[AxisSpecification]
    """Characteristics of the primary Y axis of this subplot."""

    y_axes: Optional[list[AxisSpecification]]
    """Characteristics of the secondry, tertiary, etc Y axes of this subplot."""

    xy_plots: list[XYPlotSpecification]
    """Plots of XY data for this subplot."""

    legend: Optional[LegendSpecification]
    """Characteristics of the legend for this subplot."""


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

    title: Optional[str]
    """Title (suptitle) of figure."""

    n_subfigure_rows: int = 1
    n_subfigure_cols: int = 1

    evaluation_context: Optional[list[SymbolExpression]]
    """Symbols available to other expressions in this figure specification."""

    subfigures: list[SubfigureSpecification]
