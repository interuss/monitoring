import importlib
import inspect
import pkgutil
from typing import Type


def import_submodules(module) -> None:
    """Ensure that all descendant modules of a module are loaded.

    Calling this method ensures that any descendant module can be found by name.

    :param module: Parent module from which to start explicitly importing modules.
    """
    for loader, module_name, is_pkg in pkgutil.walk_packages(
        module.__path__, module.__name__ + "."
    ):
        importlib.import_module(module_name)


def get_module_object_by_name(parent_module, object_name: str):
    module_object = parent_module
    for component in object_name.split("."):
        if not hasattr(module_object, component):
            raise ValueError(
                "Could not find component {} defined in {} while trying to locate {}".format(
                    component, module_object.__name__, object_name
                )
            )
        module_object = getattr(module_object, component)
    return module_object


def fullname(class_type: Type) -> str:
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
