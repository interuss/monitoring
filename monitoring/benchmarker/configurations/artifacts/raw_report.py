from implicitdict import ImplicitDict


class RawReportSpecification(ImplicitDict):
    name: str
    """Machine-level name for this report.  Used as the output file name."""
