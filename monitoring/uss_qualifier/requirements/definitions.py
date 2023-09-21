from __future__ import annotations
import os
from typing import Optional, List

from implicitdict import ImplicitDict


class RequirementID(str):
    """Identifier for a requirement.

    Form: <PACKAGE>.<NAME>

    PACKAGE is a Python-style package reference to a .md file (without extension)
    relative to uss_qualifier/requirements.  For instance, the PACKAGE for the file
    located at uss_qualifier/requirements/astm/f3548/v21.md would be
    `astm.f3548.v21`.

    NAME is an identifier defined in the file described by PACKAGE by enclosing it
    in a <tt> tag; for instance: `<tt>USS0105</tt>`.
    """

    def __new__(cls, value):
        illegal_characters = "#%&{}\\<>*?/ $!'\":@+`|="
        if any(c in value for c in illegal_characters):
            raise ValueError(
                f'RequirementID "{value}" may not contain any of these characters: {illegal_characters}'
            )
        str_value = str.__new__(cls, value)
        return str_value

    def md_file_path(self) -> str:
        parts = self.split(".")
        md_filename = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.path.join(*parts[0:-1]) + ".md")
        )
        return md_filename

    def short_requirement_name(self) -> str:
        parts = self.split(".")
        return parts[-1]

    def package(self) -> PackageID:
        parts = self.split(".")
        return PackageID(".".join(parts[:-1]))


class PackageID(str):
    """Identifier for a package containing requirements.

    Form: <FOLDERS>.md_file_name_without_extension

    PackageID is a Python-style package reference to a .md file (without extension)
    relative to uss_qualifier/requirements.  For instance, the PackageID for the file
    located at uss_qualifier/requirements/astm/f3548/v21.md would be
    `astm.f3548.v21`.
    """

    def __new__(cls, value):
        illegal_characters = "#%&{}\\<>*?/ $!'\":@+`|="
        if any(c in value for c in illegal_characters):
            raise ValueError(
                f'PackageID "{value}" may not contain any of these characters: {illegal_characters}'
            )
        str_value = str.__new__(cls, value)
        return str_value

    def md_file_path(self) -> str:
        parts = self.split(".")
        md_filename = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.path.join(*parts) + ".md")
        )
        return md_filename


class RequirementSetID(str):
    """Identifier for a set of requirements.

    The form of a value is a Python-style package reference to a .md file (without
    extension) relative to uss_qualifier/requirements.  For instance, the set of
    requirements described in uss_qualifier/requirements/astm/f3548/v21/scd.md would
    have a RequirementSetID of "astm.f3548.v21.scd".

    The value may have an anchor suffix composed of the character "#" followed by a
    section title.  For instance, to refer to all the requirements in the section
    entitled "Automated testing" in uss_qualifier/requirements/astm/f3548/v21/scd.md,
    the RequirementSetID would be "astm.f3548.v21.scd#Automated testing".
    """

    def __new__(cls, value):
        if "#" in value:
            parts = value.split("#")
            if len(parts) > 2:
                raise ValueError(
                    f"Only one # character is allowed in a requirement set ID; instead found {len(parts)} in '{value}'"
                )
            base_id = parts[0]
        else:
            base_id = value
        illegal_characters = "#%&{}\\<>*?/ $!'\":@+`|="
        if any(c in base_id for c in illegal_characters):
            raise ValueError(
                f'RequirementSetID "{value}" may not contain any of these characters outside its anchor: {illegal_characters}'
            )
        str_value = str.__new__(cls, value)
        return str_value

    @property
    def base_id(self) -> str:
        if "#" in self:
            return self.split("#")[0]
        else:
            return self

    @property
    def anchor(self) -> str:
        if "#" in self:
            return self.split("#")[1]
        else:
            return ""


class RequirementCollection(ImplicitDict):
    requirements: Optional[List[RequirementID]]
    """This collection includes all of these requirements."""

    requirement_sets: Optional[List[RequirementSetID]]
    """This collection includes all requirements in all of these requirement sets."""

    requirement_collections: Optional[List[RequirementCollection]]
    """This collection includes all of the requirements in all of these requirement collections."""

    exclude: Optional[RequirementCollection]
    """This collection does not include any of these requirements, despite all previous fields."""
