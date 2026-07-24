from typing import Optional

from implicitdict import ImplicitDict

from monitoring.benchmarker.configurations.artifacts.matplotlib_figure import (
    MatplotlibFigureSpecification,
)
from monitoring.benchmarker.configurations.artifacts.raw_report import (
    RawReportSpecification,
)


class ArtifactSpecification(ImplicitDict):
    raw_report: Optional[RawReportSpecification]
    matplotlib_figure: Optional[MatplotlibFigureSpecification]
