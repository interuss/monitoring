import json
from typing import TypeVar
from implicitdict import ImplicitDict


ImplicitDictType = TypeVar("ImplicitDictType", bound=ImplicitDict)


def apply_overrides(
    base_object: ImplicitDictType, overrides: dict, parse_result: bool = True
) -> ImplicitDictType:
    """Returns a copy of base_object onto which overrides were applied."""

    cpy = ImplicitDict.parse(
        json.loads(json.dumps(base_object)),
        type(base_object),
    )
    overridden = _apply_overrides(cpy, overrides)
    if parse_result:
        return ImplicitDict.parse(
            overridden,
            type(base_object),
        )
    else:
        return overridden


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
            src_field = field
            if field.startswith("+"):
                replace = True
                field = field[1:]
            else:
                replace = False
            if field in base_object and base_object[field] is not None and not replace:
                result[field] = _apply_overrides(
                    base_object[field], overrides[src_field]
                )
            else:
                result[field] = overrides[src_field]
        return result

    else:
        return overrides
