"""Base class for load-test generators. One subclass per file in this package."""

import requests


class BenchTest:
    name: str = "base"
    scopes: list[str] = []
    default: bool = True

    def setup(self, session: requests.Session, base_url: str) -> None:
        """Optional one-off prep per worker (e.g. seed data)."""

    def prepare(self, cfg, targets: list[tuple[str, str]]) -> None:
        """Optional one-time setup before workers start, run once in the parent
        (e.g. create a covering subscription). targets is [(base_url, audience)]."""

    def action(self, session: requests.Session, base_url: str) -> None:
        """A single measured unit of work. Raise on failure."""
        raise NotImplementedError

    def teardown(self, session: requests.Session, base_url: str) -> None:
        """Optional cleanup per worker."""
