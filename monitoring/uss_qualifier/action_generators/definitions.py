from typing import TypeVar, Dict

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.resources.definitions import ResourceID


GeneratorTypeName = str
"""This plain string represents a type of action generator, expressed as a Python class name qualified relative to the `uss_qualifier` module"""


ActionGeneratorSpecificationType = TypeVar(
    "ActionGeneratorSpecificationType", bound=ImplicitDict
)


class ActionGeneratorDefinition(ImplicitDict):
    generator_type: GeneratorTypeName
    """Type of action generator"""

    specification: dict = {}
    """Specification of action generator; format is the ActionGeneratorSpecificationType that corresponds to the `generator_type`"""

    resources: Dict[ResourceID, ResourceID]
    """Mapping of the ID a resource will be known by in the child action -> the ID a resource is known by in the parent test suite.

    The child action resource ID <key> is supplied by the parent test suite resource ID <value>.

    Resources not included in this field will not be available to the child action.

    If the parent resource ID is suffixed with ? then the resource will not be required (and will not be populated for the child action when not present in the parent)
    """
