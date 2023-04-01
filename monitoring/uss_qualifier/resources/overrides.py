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
    return _apply_overrides(cpy, overrides)


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
        result = ImplicitDict.parse(base_object, type(base_object))
        for field in overrides:
            if field in base_object and base_object[field] is not None:
                result[field] = _apply_overrides(base_object[field], overrides[field])
            else:
                result[field] = overrides[field]
        return result

    else:
        return overrides
