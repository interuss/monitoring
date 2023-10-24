import json
from typing import TypeVar
from implicitdict import ImplicitDict


ImplicitDictType = TypeVar("ImplicitDictType", bound=ImplicitDict)


def apply_overrides(base_object: ImplicitDictType, overrides: dict) -> ImplicitDictType:
    """Returns a copy of base_object onto which overrides were applied."""

    cpy = ImplicitDict.parse(
        json.loads(json.dumps(base_object)),
        type(base_object),
    )
    return ImplicitDict.parse(
        _apply_overrides(cpy, overrides),
        type(base_object),
    )


def apply_overrides_without_parse_type(
    base_object: ImplicitDictType, overrides: dict
) -> ImplicitDictType:
    """Returns a Dict with overrides applied, and no parsing into base object."""

    cpy = ImplicitDict.parse(
        json.loads(json.dumps(base_object)),
        type(base_object),
    )
    return (_apply_overrides(cpy, overrides),)


def _apply_overrides(base_object, overrides):
    if base_object is None:
        return overrides

    elif isinstance(overrides, list):
        result_list = []
        n_base = len(base_object)
        n_overrides = len(overrides)
        for i in range(max(n_base, n_overrides)):
            if i >= n_base:
                result_list.append(overrides[i])
            elif i >= n_overrides:
                result_list.append(base_object[i])
            else:
                result_list.append(_apply_overrides(base_object[i], overrides[i]))
        return result_list

    elif isinstance(overrides, dict):
        if isinstance(base_object, dict):
            result = {k: v for k, v in base_object.items()}
        else:
            raise ValueError(
                f"Attempted to override field with type {type(base_object)} with type {type(overrides)} ({json.dumps(base_object)} -> {json.dumps(overrides)})"
            )
        for field in overrides:
            if field.startswith("+"):
                replace = True
                field = field[1:]
            else:
                replace = False
            if field in base_object and base_object[field] is not None and not replace:
                result[field] = _apply_overrides(base_object[field], overrides[field])
            else:
                result[field] = overrides[field]
        return result

    else:
        return overrides
