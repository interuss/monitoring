"""Base class for load-test generators. One subclass per file in this package."""

import requests


class BenchTest:
    name: str = "base"
    scopes: list[str] = []
    default: bool = True

    def setup(self, session: requests.Session, base_url: str) -> None:
        """Optional one-off prep per worker (e.g. seed data)."""

    def action(self, session: requests.Session, base_url: str) -> None:
        """A single measured unit of work. Raise on failure."""
        raise NotImplementedError

    def teardown(self, session: requests.Session, base_url: str) -> None:
        """Optional cleanup per worker."""
