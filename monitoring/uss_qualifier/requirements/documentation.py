import os
from typing import Dict, Set, List, Optional

from implicitdict import ImplicitDict
import marko
import marko.element
import marko.inline

from monitoring.uss_qualifier.documentation import text_of
from monitoring.uss_qualifier.requirements.definitions import (
    RequirementCollection,
    RequirementID,
    RequirementSetID,
    PackageID,
)


class Requirement(object):
    def __init__(self, requirement_id: RequirementID):
        self.requirement_id = requirement_id


_verified_requirements: Set[RequirementID] = set()


def _verify_requirements(parent: marko.element.Element, package: PackageID) -> None:
    if hasattr(parent, "children") and not isinstance(parent.children, str):
        for i, child in enumerate(parent.children):
            if isinstance(child, str):
                continue
            if (
                i < len(parent.children) - 2
                and isinstance(child, marko.inline.InlineHTML)
                and child.children == "<tt>"
                and isinstance(parent.children[i + 2], marko.inline.InlineHTML)
                and parent.children[i + 2].children == "</tt>"
            ):
                name = text_of(parent.children[i + 1])
                _verified_requirements.add(RequirementID(package + "." + name))
            else:
                _verify_requirements(child, package)


def _load_requirement(requirement_id: RequirementID) -> None:
    md_filename = requirement_id.md_file_path()
    if not os.path.exists(md_filename):
        raise ValueError(
            f'Could not load requirement "{requirement_id}" because the file "{md_filename}" does not exist'
        )
    with open(md_filename, "r") as f:
        doc = marko.parse(f.read())
    _verify_requirements(doc, requirement_id.package())
    if requirement_id not in _verified_requirements:
        raise ValueError(
            f'Requirement "{requirement_id.short_requirement_name()}" could not be found in "{md_filename}", so the requirement {requirement_id} could not be loaded (the file must contain `<tt>{requirement_id.short_requirement_name()}</tt>` somewhere in it, but does not)'
        )


def get_requirement(requirement_id: RequirementID) -> Requirement:
    if requirement_id not in _verified_requirements:
        _load_requirement(requirement_id)
    return Requirement(requirement_id)


class RequirementSet(ImplicitDict):
    name: str
    requirement_ids: List[RequirementID]


REQUIREMENT_SET_SUFFIX = " requirement set"


_requirement_sets: Dict[RequirementSetID, RequirementSet] = {}


def _length_of_section(values, start_of_section: int) -> int:
    level = values[start_of_section].level
    c = start_of_section + 1
    while c < len(values):
        if isinstance(values[c], marko.block.Heading) and values[c].level == level:
            return c - start_of_section - 1
        c += 1
    return c - start_of_section  # end of file


def _find_section(values, section_title: str) -> int:
    for c in range(len(values)):
        if (
            isinstance(values[c], marko.block.Heading)
            and text_of(values[c]) == section_title
        ):
            return c
    return -1


def _parse_requirements(
    parent: marko.element.Element, start_index: int = 0, end_index: int = 0
) -> List[RequirementID]:
    reqs = []
    if hasattr(parent, "children") and not isinstance(parent.children, str):
        if end_index <= start_index:
            end_index = len(parent.children)
        for i in range(start_index, end_index):
            child = parent.children[i]
            if isinstance(child, str):
                continue
            if isinstance(child, marko.inline.StrongEmphasis):
                req_id = text_of(parent.children[i])
                reqs.append(RequirementID(req_id))
            else:
                reqs.extend(_parse_requirements(child))
    return reqs


def _load_requirement_set(requirement_set_id: RequirementSetID) -> RequirementSet:
    parts = requirement_set_id.base_id.split(".")
    md_filename = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.join(*parts) + ".md")
    )
    if not os.path.exists(md_filename):
        raise ValueError(
            f'Could not load requirement set "{requirement_set_id}" because the file "{md_filename}" does not exist'
        )
    with open(md_filename, "r") as f:
        doc = marko.parse(f.read())

    # Extract the file-level name from the first top-level header
    if (
        not isinstance(doc.children[0], marko.block.Heading)
        or doc.children[0].level != 1
        or not text_of(doc.children[0]).lower().endswith(REQUIREMENT_SET_SUFFIX)
    ):
        raise ValueError(
            f'The first line of {md_filename} must be a level-1 heading with the name of the scenario + "{REQUIREMENT_SET_SUFFIX}" (e.g., "# ASTM F3411-19 Service Provider requirement set")'
        )
    file_level_name = text_of(doc.children[0])[0 : -len(REQUIREMENT_SET_SUFFIX)]

    anchor = requirement_set_id.anchor
    requirement_set_name = f"{file_level_name}: {anchor}" if anchor else file_level_name

    if anchor:
        start_index = _find_section(doc.children, anchor)
        if start_index == -1:
            raise ValueError(
                f"Could not find section entitled '{anchor}' in {md_filename}"
            )
        end_index = start_index + _length_of_section(doc.children, start_index)
    else:
        start_index = 0
        end_index = 0
    reqs = _parse_requirements(doc, start_index, end_index)
    for req in reqs:
        try:
            get_requirement(req)
        except ValueError as e:
            raise ValueError(
                f'Error loading requirement set "{requirement_set_id}" from {md_filename}: {str(e)}'
            )
    return RequirementSet(name=requirement_set_name, requirement_ids=reqs)


def get_requirement_set(requirement_set_id: RequirementSetID) -> RequirementSet:
    if requirement_set_id not in _requirement_sets:
        _requirement_sets[requirement_set_id] = _load_requirement_set(
            requirement_set_id
        )
    return _requirement_sets[requirement_set_id]


def resolve_requirements_collection(
    collection: RequirementCollection,
) -> Set[RequirementID]:
    """Compute the set of requirement IDs identified by the specified requirements collection.

    Args:
        collection: Specified requirements collection.

    Returns: Set of IDs of requirements identified by the specified collection.
    """
    reqs: Set[RequirementID] = set()

    if "requirements" in collection and collection.requirements:
        for req_id in collection.requirements:
            reqs.add(req_id)

    if "requirement_sets" in collection and collection.requirement_sets:
        for req_set_id in collection.requirement_sets:
            req_set = get_requirement_set(req_set_id)
            for req_id in req_set.requirement_ids:
                reqs.add(req_id)

    if "requirement_collections" in collection and collection.requirement_collections:
        for also_include in collection.requirement_collections:
            for req_id in resolve_requirements_collection(also_include):
                reqs.add(req_id)

    if "exclude" in collection and collection.exclude:
        for req_id in resolve_requirements_collection(collection.exclude):
            reqs.remove(req_id)

    return reqs
