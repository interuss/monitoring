"""Base class for experiments that sweep across a range of values. A Sweep yields contexts for each value in the range, and contexts are sets of environment variables that are used in `make start-locally` before a measurement."""

from dataclasses import dataclass


@dataclass
class Variant:
    label: str
    """Label of the characteristic of interest in this context, e.g. '50ms'"""
    env: dict[str, str]
    """Additional environment variable values for `make start-locally`"""


class Sweep:
    name: str = "base"
    """Name of the sweep, used for user selection and internal key"""

    variable_label: str = "context"
    """Label of the value being swept, useful for labeling the axis in which the contexts are displayed"""

    def variants(self) -> list[Variant]:
        raise NotImplementedError
