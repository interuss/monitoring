"""Base class for context generators. A context yields environment variants
that are applied to `make start-locally` before a measurement."""

from dataclasses import dataclass


@dataclass
class Variant:
    label: str  # x-axis label, e.g. "50ms"
    env: dict[str, str]  # extra env for start-locally


class Context:
    name: str = "base"
    axis_label: str = "context"  # descriptive x-axis label

    def variants(self) -> list[Variant]:
        raise NotImplementedError
