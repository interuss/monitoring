"""Auto-discover Context subclasses defined in this package."""

import importlib
import inspect
import pkgutil

from monitoring.dss_bench.contexts.base import Context


def discover() -> dict[str, type[Context]]:
    found: dict[str, type[Context]] = {}
    for info in pkgutil.iter_modules(__path__):
        if info.name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, Context)
                and obj is not Context
                and obj.__module__ == module.__name__
            ):
                found[obj.name] = obj
    return found
