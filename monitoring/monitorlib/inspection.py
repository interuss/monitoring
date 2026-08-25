import importlib
import inspect
import pkgutil
from typing import Any, Optional

from implicitdict import ImplicitDict

_modules_imported = set()


def import_submodules(module) -> None:
    """Ensure that all descendant modules of a module are loaded.

    Calling this method ensures that any descendant module can be found by name.

    :param module: Parent module from which to start explicitly importing modules.
    """
    if module in _modules_imported:
        return
    for loader, module_name, is_pkg in pkgutil.walk_packages(
        module.__path__, module.__name__ + "."
    ):
        importlib.import_module(module_name)
    _modules_imported.add(module)


def get_module_object_by_name(parent_module, object_name: str):
    module_object = parent_module
    for component in object_name.split("."):
        if not hasattr(module_object, component):
            raise ValueError(
                f"Could not find component {component} defined in {module_object.__name__} while trying to locate {object_name}"
            )
        module_object = getattr(module_object, component)
    return module_object


def fullname(class_type: type) -> str:
    module = class_type.__module__
    if module == "builtins":
        if hasattr(class_type, "__qualname__"):
            return class_type.__qualname__  # avoid outputs like 'builtins.str'
        else:
            return str(class_type)
    if hasattr(class_type, "__qualname__"):
        return module + "." + class_type.__qualname__
    else:
        return str(class_type)


def calling_function_name(levels: int = 0) -> str:
    return inspect.stack()[levels + 1].function


class AttributeValuePair(ImplicitDict):
    name: str
    """The attribute that is expected to have a particular value.
    
    Nested attributes are accepted (e.g., `"foo.bar"`)."""

    equals_string_value: Optional[str]
    """The attribute value is this string."""

    equals_number_value: Optional[float]
    """The attribute value is this number."""


def _has_attr(obj: Any, attr_name: str) -> bool:
    if "." in attr_name:
        levels = attr_name.split(".")
        if not hasattr(obj, levels[0]):
            return False
        return _has_attr(getattr(obj, levels[0]), ".".join(levels[1:]))
    else:
        return hasattr(obj, attr_name)


def _get_attr_value(obj: Any, attr_name: str) -> Any:
    if "." in attr_name:
        base, remaining = attr_name.split(".", 1)
        return _get_attr_value(getattr(obj, base), remaining)
    else:
        return getattr(obj, attr_name)


def evaluate_attributes(
    obj: Any,
    expectations: list[AttributeValuePair],
) -> list[str]:
    """Evaluates an object against a set of AttributeValuePair expectations.

    Returns:
        A list of string descriptions detailing any failed expectations. An empty list signifies success.
    """
    failures: list[str] = []
    for pair in expectations:
        attr_name = pair.name
        if not _has_attr(obj, attr_name):
            failures.append(
                f"Required attribute '{attr_name}' is entirely absent from the object."
            )
            continue

        actual_val = _get_attr_value(obj, attr_name)

        if "equals_string_value" in pair and pair.equals_string_value is not None:
            if not isinstance(actual_val, str):
                failures.append(
                    f"Attribute '{attr_name}' expected to be of type 'str', but observed type '{type(actual_val).__name__}'."
                )
            elif actual_val != pair.equals_string_value:
                failures.append(
                    f"Attribute '{attr_name}': Expected string value '{pair.equals_string_value}', but observed '{actual_val}'."
                )

        if "equals_number_value" in pair and pair.equals_number_value is not None:
            if not isinstance(actual_val, (int, float)):
                failures.append(
                    f"Attribute '{attr_name}' expected to be numeric, but observed type '{type(actual_val).__name__}'."
                )
            elif actual_val != pair.equals_number_value:
                failures.append(
                    f"Attribute '{attr_name}': Expected numeric value {pair.equals_number_value}, but observed {actual_val}."
                )

    return failures
