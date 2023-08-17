import json
from typing import List, Tuple, Any, Union

from implicitdict import ImplicitDict

JSONPath = str
"""Search path following JSON Path rules.

May match 0, 1, or many items.

Example: $..*[?(@.suite_type=="suites.astm.netrid.f3411_22a")]"""

JSONAddress = str
"""JSONPath-like address of a particular element within a (potentially) nested dict.

Will match either 0 or 1 item.

Example: things[2].foo.bar[0]"""


def get_element(obj: dict, element: Union[JSONAddress, List[str]], pop=False) -> Any:
    """Get a descendant element from obj, optionally popping (removing) it from obj.

    Args:
        obj: The ancestor object to which the JSONAddress is relative.
        element: Location of element to get/pop.
          * JSONAddress: single string literal indicating location
          * List[str]: list of dict layers describing location; formed by splitting JSONAddress by "."
        pop: If True, remove the element once found and returned.

    Returns: Element at specified location within obj.
    """
    try:
        if isinstance(element, str):
            return get_element(obj, element.split("."), pop)
        if not element:
            return obj
        if element[0] == "$" or element[0] == "":
            return get_element(obj, element[1:], pop)

        if len(element) == 1:
            field = element[0]
            if field[-1] == "]" and "[" in field:
                field, index = field[0:-1].split("[")
                index = int(index)
                items = obj[field]
                result = items[index]
                if pop:
                    del items[index]
                return result
            else:
                if pop:
                    return obj.pop(field)
                else:
                    return obj[field]
        else:
            child = get_element(obj, [element[0]])
            return get_element(child, element[1:], pop)
    except KeyError as e:
        raise ValueError(f"{str(e)} at {element}")
    except ValueError as e:
        raise ValueError(f"{str(e)} at {element}")


class RemovedElement(ImplicitDict):
    address: JSONAddress
    value = None


def remove_elements(
    src: dict, elements_to_remove: List[JSONAddress]
) -> Tuple[dict, List[RemovedElement]]:
    """Remove a list of elements from the src dict.

    Args:
        src: dict from which elements should be removed.
        elements_to_remove: List of elements to remove from src, in order.

    Returns:
        * A deep copy of src with elements_to_remove removed.
        * A list of RemovedElements containing the values removed.
    """
    less = json.loads(json.dumps(src))
    removed: List[RemovedElement] = []
    for element in elements_to_remove:
        try:
            removed_value = get_element(less, element, pop=True)
        except ValueError:
            continue
        removed.append(RemovedElement(address=element, value=removed_value))
    return less, removed
