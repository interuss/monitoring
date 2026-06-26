"""Auto-discover BenchTest subclasses defined in this package."""

import importlib
import inspect
import pkgutil

from monitoring.dss_bench.tests.base import BenchTest


def discover() -> dict[str, type[BenchTest]]:
    found: dict[str, type[BenchTest]] = {}
    for info in pkgutil.iter_modules(__path__):
        if info.name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BenchTest)
                and obj is not BenchTest
                and obj.__module__ == module.__name__
            ):
                found[obj.name] = obj
    return found
