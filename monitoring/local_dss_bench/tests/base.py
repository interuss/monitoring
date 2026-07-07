"""Base class for load-test generators. One subclass per file in this package."""

import requests


class BenchTest:
    name: str = "base"
    """Name of the test, used for user selection and internal key"""

    scopes: list[str] = []
    """List of requiered scopes"""

    default: bool = True
    """If true, test is run when user don't select test"""

    def setup(self, session: requests.Session, base_url: str) -> None:
        """Optional one-off prep per worker (e.g. seed data)."""

    def action(self, session: requests.Session, base_url: str) -> None:
        """A single measured unit of work. Raise on failure."""
        raise NotImplementedError

    def teardown(self, session: requests.Session, base_url: str) -> None:
        """Optional cleanup per worker."""
