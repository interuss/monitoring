from typing import Optional

from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.resource import Resource


class TestExclusionsSpecification(ImplicitDict):
    allow_private_addresses: Optional[bool]
    allow_cleartext_queries: Optional[bool]


class TestExclusionsResource(Resource[TestExclusionsSpecification]):
    """TestExclusionsResource enables control over test behavior. Should always be optional when used."""

    _spec: TestExclusionsSpecification

    def __init__(
        self,
        specification: TestExclusionsSpecification,
    ):
        self._spec = specification

    @property
    def allow_private_addresses(self) -> bool:
        """Whether the test should allow private addresses that are not publicly addressable. Defaults to False if not set."""
        if self._spec.has_field_with_value("allow_private_addresses"):
            return self._spec.allow_private_addresses
        return False

    @property
    def allow_cleartext_queries(self) -> bool:
        """Whether the test should allow cleartext HTTP queries. Defaults to False if not set."""
        if self._spec.has_field_with_value("allow_cleartext_queries"):
            return self._spec.allow_cleartext_queries
        return False
