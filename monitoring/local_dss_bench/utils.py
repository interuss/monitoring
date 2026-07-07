import importlib
import inspect
import pkgutil
from collections.abc import Iterable


def discover[T](pkg: str, path: Iterable[str], base: type[T]) -> Iterable[type[T]]:
    """Return the list of subclasses of a specfic package"""

    found: list[type[T]] = []
    for info in pkgutil.iter_modules(path):
        if info.name == "base":
            continue
        module = importlib.import_module(f"{pkg}.{info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, base)
                and obj is not base
                and obj.__module__ == module.__name__
            ):
                found.append(obj)
    return found
