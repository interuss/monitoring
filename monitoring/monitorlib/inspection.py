import importlib
import inspect
import pkgutil
import types
from typing import Any, Optional, TypeVar, get_args, get_origin

from implicitdict import ImplicitDict

from monitoring.monitorlib.typing import ResolvedType, TypeExpression, TypeName

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


def _split_type_args(args_str: str, full_expr: TypeExpression) -> list[TypeExpression]:
    """Get the TypeExpressions from a generic argument list.

    Args:
      * args_str: Generic argument list; e.g. "Foo[Bar[Baz]], Booz"
      * full_expr: Context in which the argument list was used; only used for better error messages.

    Returns: List of TypeExpressions from args_str; e.g., "Foo[Bar[Baz]]", "Booz"
    """
    arg_strs: list[TypeExpression] = []
    depth = 0
    current: list[str] = []
    for ch in args_str:
        if ch == "[":
            depth += 1
            current.append(ch)
        elif ch == "]":
            depth -= 1
            if depth < 0:
                raise ValueError(
                    f"Malformed type expression '{full_expr}': unbalanced brackets"
                )
            current.append(ch)
        elif ch == "," and depth == 0:
            arg_str = "".join(current).strip()
            if not arg_str:
                raise ValueError(
                    f"Malformed type expression '{full_expr}': empty type argument"
                )
            arg_strs.append(arg_str)
            current = []
        else:
            current.append(ch)
    if depth != 0:
        raise ValueError(
            f"Malformed type expression '{full_expr}': unbalanced brackets"
        )
    last_arg = "".join(current).strip()
    if not last_arg:
        raise ValueError(
            f"Malformed type expression '{full_expr}': empty type argument"
        )
    arg_strs.append(last_arg)
    return arg_strs


def resolve_type_expression(
    parent_module: types.ModuleType, type_expr: TypeExpression
) -> ResolvedType:
    """Resolve a TypeExpression (qualified relative to `parent_module`, optionally with generic `[...]` arguments) into a ResolvedType."""
    type_expr = type_expr.strip()
    if not type_expr:
        raise ValueError("Type expression cannot be empty")

    if "[" not in type_expr:
        if "]" in type_expr:
            raise ValueError(f"Malformed type expression '{type_expr}': unexpected ']'")
        if type_expr in ("ImplicitDict", "implicitdict.ImplicitDict"):
            return ImplicitDict
        resolved = get_module_object_by_name(parent_module, type_expr)
        if isinstance(resolved, (type, types.GenericAlias)):
            return resolved
        resolved_origin = get_origin(resolved)
        if isinstance(resolved_origin, type):
            resolved_args = get_args(resolved)
            return resolved_origin.__class_getitem__(
                resolved_args[0] if len(resolved_args) == 1 else resolved_args
            )
        raise ValueError(f"'{type_expr}' did not resolve to a type")

    if not type_expr.endswith("]"):
        raise ValueError(
            f"Malformed type expression '{type_expr}': expected trailing ']'"
        )

    bracket_idx = type_expr.index("[")
    base_name: TypeName = type_expr[:bracket_idx].strip()
    inner = type_expr[bracket_idx + 1 : -1].strip()
    if not base_name or not inner:
        raise ValueError(f"Malformed type expression '{type_expr}'")

    base_cls = get_module_object_by_name(parent_module, base_name)
    if not isinstance(base_cls, type):
        raise ValueError(f"'{base_name}' did not resolve to a type")
    arg_strs = _split_type_args(inner, type_expr)
    resolved_args = tuple(resolve_type_expression(parent_module, a) for a in arg_strs)

    params: tuple[TypeVar, ...] = getattr(base_cls, "__parameters__", ())
    if not params:
        raise ValueError(
            f"Type {base_name} is not generic and does not accept type arguments"
        )

    if len(resolved_args) == len(params):
        full_args = resolved_args
    elif (
        len(resolved_args) == len(params) - 1
        and len(params) >= 2
        and getattr(params[0], "__bound__", None) is ImplicitDict
    ):
        first_origin = get_origin(resolved_args[0]) or resolved_args[0]
        if not (
            isinstance(first_origin, type) and issubclass(first_origin, ImplicitDict)
        ):
            full_args = (ImplicitDict, *resolved_args)
        else:
            raise ValueError(
                f"Type {base_name} expects {len(params)} type arguments, but {len(resolved_args)} were provided"
            )
    else:
        raise ValueError(
            f"Type {base_name} expects {len(params)} type arguments, but {len(resolved_args)} were provided"
        )

    return base_cls.__class_getitem__(
        full_args[0] if len(full_args) == 1 else full_args
    )


def resolve_type_and_args[T](
    parent_module: types.ModuleType,
    type_expr: TypeExpression,
    base_class: type[T],
) -> tuple[type[T], tuple[ResolvedType, ...]]:
    """Parse and resolve a TypeExpression (which may include generic `[...]` arguments) relative to `parent_module` into its origin class (validated to be a subclass of `base_class`) and resolved type arguments."""
    resolved = resolve_type_expression(parent_module, type_expr)
    origin = get_origin(resolved) or resolved
    args: tuple[ResolvedType, ...] = get_args(resolved)
    if not isinstance(origin, type) or not issubclass(origin, base_class):
        raise NotImplementedError(
            f"Type {getattr(origin, '__name__', str(origin))} is not a subclass of the {base_class.__name__} base class"
        )
    return origin, args


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
    """The attribute value is exactly this number.  Note that this may not be the desirable behavior when comparing float values."""


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
