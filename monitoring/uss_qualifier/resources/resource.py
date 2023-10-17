from abc import ABC, abstractmethod
from typing import get_type_hints, Dict, Generic, Tuple, TypeVar, Type

from implicitdict import ImplicitDict

from monitoring import uss_qualifier as uss_qualifier_module
from monitoring.monitorlib import inspection
from monitoring.uss_qualifier import resources as resources_module
from monitoring.uss_qualifier.resources.definitions import (
    ResourceDeclaration,
    ResourceID,
)

SpecificationType = TypeVar("SpecificationType", bound=ImplicitDict)


class Resource(ABC, Generic[SpecificationType]):
    @abstractmethod
    def __init__(self, specification: SpecificationType, **dependencies):
        """Create an instance of the resource.

        Concrete subclasses of Resource must implement their constructor according to this specification.

        :param specification: A serializable (subclass of implicitdict.ImplicitDict) specification for how to create the resource.
        :param dependencies: If this resource depends on any other resources, each of the other dependencies should be declared as an additional typed parameter to the constructor.  Each parameter type should be a class that is a subclass of Resource.
        """
        raise NotImplementedError(
            "A concrete resource type must implement __init__ method"
        )

    def is_type(self, resource_type: str) -> bool:
        specified_type = inspection.get_module_object_by_name(
            uss_qualifier_module, resource_type
        )
        return self.__class__ == specified_type


ResourceType = TypeVar("ResourceType", bound=Resource)


class MissingResourceError(ValueError):
    missing_resource_name: str

    def __init__(self, msg: str, missing_resource_name: str):
        super(MissingResourceError, self).__init__(msg)
        self.missing_resource_name = missing_resource_name


def create_resources(
    resource_declarations: Dict[ResourceID, ResourceDeclaration]
) -> Dict[ResourceID, ResourceType]:
    """Instantiate all resources from the provided declarations.

    Note that some declarations, such as resources whose specifications contain ExternalFiles, may be mutated while the
    resource is loaded.

    Args:
        resource_declarations: Mapping between resource ID and declaration for that resource.

    Returns: Mapping between resource ID and an instance of that declared resource.
    """
    resource_pool: Dict[ResourceID, ResourceType] = {}

    resources_created = 1
    unmet_dependencies_by_resource = {}
    while resources_created > 0:
        resources_created = 0
        for name, declaration in resource_declarations.items():
            if name in resource_pool:
                continue
            unmet_dependencies = [
                d for d in declaration.dependencies.values() if d not in resource_pool
            ]
            if unmet_dependencies:
                unmet_dependencies_by_resource[name] = unmet_dependencies
            else:
                resource_pool[name] = _make_resource(declaration, resource_pool)
                resources_created += 1

    if len(resource_pool) != len(resource_declarations):
        uncreated_resources = [
            (r + " ({} missing)".format(", ".join(unmet_dependencies_by_resource[r])))
            for r in resource_declarations
            if r not in resource_pool
        ]
        raise ValueError(
            "Could not create resources: {} (do you have circular dependencies?)".format(
                ", ".join(uncreated_resources)
            )
        )

    return resource_pool


_resources_module_imported = False


def get_resource_types(
    declaration: ResourceDeclaration,
) -> Tuple[Type[Resource], Type[ImplicitDict]]:
    """Get the resource and specification types from the declaration, validating against the resource's constructor signature.

    Args:
        declaration: Resource declaration for which to obtain types

    Returns:
        * Concrete Resource subclass type of the declared resource
        * Specification type for the declared resource, or None if the resource type doesn't have a specification
    """
    global _resources_module_imported
    if not _resources_module_imported:
        inspection.import_submodules(resources_module)
        _resources_module_imported = True

    resource_type = inspection.get_module_object_by_name(
        uss_qualifier_module, declaration.resource_type
    )
    if not issubclass(resource_type, Resource):
        raise NotImplementedError(
            "Resource type {} is not a subclass of the Resource base class".format(
                resource_type.__name__
            )
        )

    constructor_signature = get_type_hints(resource_type.__init__)
    specification_type = None
    for arg_name, arg_type in constructor_signature.items():
        if arg_name == "return":
            continue
        if arg_name == "self":
            continue
        if arg_name == "specification":
            specification_type = arg_type
            continue
        if arg_name not in declaration.dependencies:
            raise ValueError(
                'Resource declaration for {} is missing a source for dependency "{}"'.format(
                    declaration.resource_type, arg_type
                )
            )

    return resource_type, specification_type


def _make_resource(
    declaration: ResourceDeclaration, resource_pool: Dict[ResourceID, Resource]
) -> Resource:
    resource_type, specification_type = get_resource_types(declaration)

    constructor_args = {}
    for arg_name, pool_source in declaration.dependencies.items():
        if pool_source not in resource_pool:
            raise ValueError(
                'Resource "{}" was not found in the resource pool when trying to create {} resource'.format(
                    pool_source, declaration.resource_type
                )
            )
        constructor_args[arg_name] = resource_pool[pool_source]
    if specification_type is not None:
        specification = ImplicitDict.parse(
            declaration.specification, specification_type
        )
        declaration.specification = specification
        constructor_args["specification"] = specification

    return resource_type(**constructor_args)


def make_child_resources(
    parent_resources: Dict[ResourceID, ResourceType],
    child_resource_map: Dict[ResourceID, ResourceID],
    subject: str,
) -> Dict[ResourceID, ResourceType]:
    child_resources = {}
    for child_id, parent_id in child_resource_map.items():
        is_optional = parent_id.endswith("?")
        if is_optional:
            parent_id = parent_id[:-1]
        if parent_id in parent_resources:
            child_resources[child_id] = parent_resources[parent_id]
        elif not is_optional:
            raise MissingResourceError(
                f'{subject} could not find required resource ID "{parent_id}" used to populate child resource ID "{child_id}"',
                parent_id,
            )
    return child_resources
