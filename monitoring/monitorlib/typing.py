import types
from typing import TypeVar, Union, get_args, get_origin

TypeName = str
"""Plain string representing a Python class/type name without generic type arguments (e.g., `resources.flight_planning.FlightPlannerResource`)."""

TypeExpression = str
"""Plain string representing a Python type qualified relative to some base module, optionally with generic type arguments in brackets (e.g., `resources.SomeGenericResource[resources.SubResource]`)."""

ResolvedType = type | types.GenericAlias
"""A resolved Python class or parameterized generic class (note: at runtime, subscripted typing.Generic subclasses produce typing._GenericAlias instances)."""

TypeAnnotation = ResolvedType | types.UnionType | TypeVar
"""A type annotation as may appear on a constructor/function parameter or generic base class."""


def substitute_typevars(
    tp: TypeAnnotation, mapping: dict[TypeVar, ResolvedType]
) -> TypeAnnotation:
    """Recursively substitute TypeVars in `tp` according to `mapping`.

    Args:
        tp: Type annotation in which to substitute TypeVars.
        mapping: Mapping from TypeVar to its resolved type.

    Returns:
        Type annotation with mapped TypeVars replaced by their resolved types.
    """
    if isinstance(tp, TypeVar):
        return mapping.get(tp, tp)
    origin = get_origin(tp)
    if origin is None:
        return tp
    args: tuple[TypeAnnotation, ...] = get_args(tp)
    if not args:
        return tp
    new_args = tuple(substitute_typevars(a, mapping) for a in args)
    if new_args == args:
        return tp
    if origin is types.UnionType or origin is Union:
        return Union.__getitem__(new_args)  # type: ignore[index]
    if isinstance(origin, type):
        return origin.__class_getitem__(new_args[0] if len(new_args) == 1 else new_args)
    return tp


def collect_typevars(cls: type, mapping: dict[TypeVar, ResolvedType]) -> None:
    """Populate `mapping` with TypeVar bindings across `cls`'s generic base class hierarchy.

    Walks `__orig_bases__` (or `__bases__` if not generic) of `cls` recursively, substituting
    any already-known TypeVars in `mapping` so that TypeVars defined on ancestor generic
    classes are mapped to their concrete or parameterized types.
    """
    orig_bases: tuple[TypeAnnotation, ...] = getattr(cls, "__orig_bases__", ())
    if orig_bases:
        for base in orig_bases:
            origin = get_origin(base)
            if origin is None:
                if isinstance(base, type) and base is not object:
                    collect_typevars(base, mapping)
                continue
            params: tuple[TypeVar, ...] = getattr(origin, "__parameters__", ())
            base_args: tuple[TypeAnnotation, ...] = get_args(base)
            for param, arg in zip(params, base_args):
                resolved = substitute_typevars(arg, mapping)
                if not isinstance(resolved, (TypeVar, types.UnionType)):
                    mapping[param] = resolved
            if isinstance(origin, type):
                collect_typevars(origin, mapping)
    else:
        for base in getattr(cls, "__bases__", ()):
            if isinstance(base, type) and base is not object:
                collect_typevars(base, mapping)


def is_type_covariant_match(
    actual_type: TypeAnnotation,
    expected_type: TypeAnnotation,
    initial_typevar_map: dict[TypeVar, ResolvedType] | None = None,
) -> bool:
    """Check whether `actual_type` is a covariant match for `expected_type`.

    Supports standard class inheritance (`issubclass`), parameterized generic types
    with covariant type argument matching across the class hierarchy, union expected
    types, and bounded TypeVars.

    Args:
        actual_type: The actual type or parameterized generic type annotation.
        expected_type: The target type or parameterized generic type annotation to check against.
        initial_typevar_map: Optional pre-populated TypeVar mapping for `actual_type`.
    """
    if isinstance(actual_type, TypeVar):
        if actual_type.__bound__ is not None:
            return is_type_covariant_match(actual_type.__bound__, expected_type)
        return False

    if get_origin(expected_type) in (types.UnionType, Union):
        expected_union_args: tuple[TypeAnnotation, ...] = get_args(expected_type)
        return any(
            is_type_covariant_match(actual_type, member, initial_typevar_map)
            for member in expected_union_args
            if member is not type(None)
        )

    actual_origin = get_origin(actual_type) or actual_type
    actual_args: tuple[TypeAnnotation, ...] = get_args(actual_type)
    expected_origin = get_origin(expected_type) or expected_type
    expected_args: tuple[TypeAnnotation, ...] = get_args(expected_type)

    if not isinstance(actual_origin, type) or not isinstance(expected_origin, type):
        return actual_type == expected_type

    if not issubclass(actual_origin, expected_origin):
        return False

    if not expected_args:
        return True

    actual_typevar_map: dict[TypeVar, ResolvedType] = (
        dict(initial_typevar_map) if initial_typevar_map else {}
    )
    actual_params: tuple[TypeVar, ...] = getattr(actual_origin, "__parameters__", ())
    for param, arg in zip(actual_params, actual_args):
        if not isinstance(arg, (TypeVar, types.UnionType)):
            actual_typevar_map[param] = arg
    collect_typevars(actual_origin, actual_typevar_map)

    expected_params: tuple[TypeVar, ...] = getattr(
        expected_origin, "__parameters__", ()
    )
    for param, exp_arg in zip(expected_params, expected_args):
        act_arg: TypeAnnotation = actual_typevar_map.get(param, param)
        if not is_type_covariant_match(act_arg, exp_arg):
            return False

    return True


def infer_typevars_from_arg(
    param_type: TypeAnnotation,
    arg_type: ResolvedType,
    target_typevars: set[TypeVar],
    typevar_map: dict[TypeVar, ResolvedType],
) -> None:
    """Infer TypeVar bindings in `target_typevars` by matching `param_type` against `arg_type`.

    Any newly inferred bindings (satisfying the TypeVar's bound, if any) are added
    in-place to `typevar_map`.
    """
    if isinstance(param_type, TypeVar):
        if param_type in target_typevars and param_type not in typevar_map:
            if param_type.__bound__ is None or is_type_covariant_match(
                arg_type, param_type.__bound__
            ):
                typevar_map[param_type] = arg_type
        return

    origin = get_origin(param_type)
    if origin in (types.UnionType, Union):
        union_args: tuple[TypeAnnotation, ...] = get_args(param_type)
        non_none = [a for a in union_args if a is not type(None)]
        if len(non_none) == 1:
            infer_typevars_from_arg(non_none[0], arg_type, target_typevars, typevar_map)
        return

    if origin is not None:
        arg_origin = get_origin(arg_type) or arg_type
        arg_args: tuple[TypeAnnotation, ...] = get_args(arg_type)
        if (
            isinstance(arg_origin, type)
            and isinstance(origin, type)
            and issubclass(arg_origin, origin)
        ):
            arg_map: dict[TypeVar, ResolvedType] = {}
            arg_params: tuple[TypeVar, ...] = getattr(arg_origin, "__parameters__", ())
            for p, a in zip(arg_params, arg_args):
                if not isinstance(a, (TypeVar, types.UnionType)):
                    arg_map[p] = a
            collect_typevars(arg_origin, arg_map)
            origin_params: tuple[TypeVar, ...] = getattr(origin, "__parameters__", ())
            param_args: tuple[TypeAnnotation, ...] = get_args(param_type)
            for p_tv, p_arg in zip(origin_params, param_args):
                if p_tv in arg_map:
                    infer_typevars_from_arg(
                        p_arg, arg_map[p_tv], target_typevars, typevar_map
                    )


def format_type_name(tp: TypeAnnotation) -> TypeName:
    """Return a human-readable display name for a type annotation."""
    return getattr(tp, "__name__", str(tp))
