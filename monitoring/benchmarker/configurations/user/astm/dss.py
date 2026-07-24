from enum import StrEnum


class ASTMDSSSelectionStrategy(StrEnum):
    First = "First"
    """Always use the first DSS in the pool list."""

    Random = "Random"
    """Use a random DSS from the pool list for every operation."""
