from functools import cmp_to_key
from typing import List, Union

from monitoring.uss_qualifier.reports.tested_requirements.data_types import (
    TestedBreakdown,
    TestedRequirement,
)


def _split_strings_numbers(s: str) -> List[Union[int, str]]:
    digits = "0123456789"
    current_number = ""
    current_string = ""
    parts = []
    for si in s:
        if si in digits:
            if current_string:
                parts.append(current_string)
                current_string = ""
            current_number += si
        else:
            if current_number:
                parts.append(int(current_number))
                current_number = ""
            current_string += si
    if current_number:
        parts.append(int(current_number))
    elif current_string:
        parts.append(current_string)
    return parts


def _requirement_id_parts(req_id: str) -> List[str]:
    """Split a requirement ID into sortable parts.

    Each ID is split into parts in multiple phases (example: astm.f3411.v22a.NET0260,Table1,1b):
      * Split at periods (splits into package and plain ID)
        * Example: ["astm", "f3411", "v22a", "NET0260,Table1,1b"]
      * Split at commas (splits portions of plain ID by convention)
        * Example: ["astm", "f3411", "v22a", "NET0260", "Table1", "1b"]
      * Split at transitions between words and numbers (so numbers are their own parts and non-numbers are their own parts)
        * Example: ["astm", "f", 3411, "v", 22, "a", "NET", 260, "Table", 1, 1, "b"]

    Args:
        req_id: Requirement ID to split.

    Returns: Constituent parts of req_id.
    """
    old_parts = req_id.split(".")
    parts = []
    for p in old_parts:
        parts.extend(p.split(","))
    old_parts = parts
    parts = []
    for p in old_parts:
        parts.extend(_split_strings_numbers(p))
    return parts


def _compare_requirement_ids(r1: TestedRequirement, r2: TestedRequirement) -> int:
    """Compare requirement IDs for the purpose of sorting.

    The requirement IDs are split into parts and then the parts compared.  If all parts are equal but one ID has more
    parts, the ID with fewer parts is first.  See _requirement_id_parts for how requirement IDs are split.

    Returns:
        * -1 if r1 should be before r2
        * 0 if r1 is equal to r2
        * 1 if r1 should be after r2
    """
    parts1 = _requirement_id_parts(r1.id)
    parts2 = _requirement_id_parts(r2.id)
    i = 0
    while i < min(len(parts1), len(parts2)):
        p1 = parts1[i]
        p2 = parts2[i]
        if p1 == p2:
            i += 1
            continue
        if isinstance(p1, int):
            if isinstance(p2, int):
                return -1 if p1 < p2 else 1
            else:
                return -1
        else:
            if isinstance(p2, int):
                return 1
            else:
                return -1 if p1 < p2 else 1
    if i == len(parts1) and i == len(parts2):
        return 0
    return -1 if len(parts1) < len(parts2) else 1


def sort_breakdown(breakdown: TestedBreakdown) -> None:
    """Sort breakdown elements by package and requirement ID."""
    breakdown.packages.sort(key=lambda p: p.id)
    for package in breakdown.packages:
        package.requirements.sort(key=cmp_to_key(_compare_requirement_ids))
        for requirement in package.requirements:
            requirement.scenarios.sort(key=lambda s: s.name)
