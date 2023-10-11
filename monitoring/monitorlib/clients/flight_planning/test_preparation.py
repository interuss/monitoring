from typing import Optional, List

from implicitdict import ImplicitDict

from monitoring.monitorlib.fetch import Query


class ClearAreaOutcome(ImplicitDict):
    success: Optional[bool] = False
    """True if, and only if, all flight plans in the specified area managed by the USS were canceled and removed."""

    message: Optional[str]
    """If the USS was unable to clear the entire area, this message can provide information on the problem encountered."""


class ClearAreaResponse(ImplicitDict):
    outcome: ClearAreaOutcome


class TestPreparationActivityResponse(ImplicitDict):
    errors: Optional[List[str]] = None
    """If any errors occurred during this activity, a list of those errors."""

    queries: List[Query]
    """Queries used to accomplish this activity."""
