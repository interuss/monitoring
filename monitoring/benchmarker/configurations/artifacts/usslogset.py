from typing import Optional

from implicitdict import ImplicitDict


class USSLogSetSpecification(ImplicitDict):
    """Specification to write ASTM F3548 DSS interactions to a USSLogSet file."""

    include_headers: Optional[list[str]]
    """If specified, only include headers with this case-insensitive key."""

    exclude_headers: Optional[list[str]]
    """If specified, omit headers with any of these case-insensitive keys."""
