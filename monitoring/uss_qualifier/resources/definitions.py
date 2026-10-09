from typing import TypeVar

from implicitdict import ImplicitDict

ResourceID = str
"""This plain string represents the ID/name of a resource"""


ResourceTypeName = str
"""This plain string represents a type of resource, expressed as a Python class name qualified relative to this `resources` module, optionally with generic type arguments in brackets (e.g., `resources.SomeGenericResource[resources.SubResource]`)"""


SpecificationType = TypeVar("SpecificationType", bound=ImplicitDict)


class ResourceDeclaration(ImplicitDict):
    resource_type: ResourceTypeName
    """Type of resource, expressed as a Python class name qualified relative to this `resources` module (optionally with generic type arguments in brackets)"""

    dependencies: dict[ResourceID, ResourceID] = {}
    """Mapping of dependency parameter (additional argument to concrete resource constructor) to `name` of resource to use (optionally suffixed with `?` to indicate an optional dependency when the constructor parameter has a default value or is accepted through **kwargs). Missing optional dependencies are omitted from the constructor call; dependencies accepted through **kwargs have an implicit default of None."""

    specification: dict = {}
    """Specification of resource; format is the SpecificationType that corresponds to the `resource_type`"""


class ResourceCollection(ImplicitDict):
    resource_declarations: dict[ResourceID, ResourceDeclaration]
    """Mapping of globally (within resource collection) unique name identifying a resource to the declaration of that resource"""
