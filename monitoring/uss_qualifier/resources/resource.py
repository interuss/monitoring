from abc import ABC
from typing import Dict, Generic, Set, Tuple, Type, TypeVar, get_type_hints

from implicitdict import ImplicitDict
from loguru import logger

from monitoring import uss_qualifier as uss_qualifier_module
from monitoring.monitorlib import inspection
from monitoring.uss_qualifier import resources as resources_module
from monitoring.uss_qualifier.resources.definitions import (
    ResourceDeclaration,
    ResourceID,
)

SpecificationType = TypeVar("SpecificationType", bound=ImplicitDict)


class Resource(ABC, Generic[SpecificationType]):
    resource_origin: str
    """The origin of this resource (usually the resource name in the top-level resource pool for a test configuration,
    though occasionally local to a test suite, derived from another resource, default, or something else)"""

    def __init__(
        self, specification: SpecificationType, resource_origin: str, **dependencies
    ):
        """Create an instance of the resource.

        Concrete subclasses of Resource must implement their constructor according to this specification.

        :param specification: A serializable (subclass of implicitdict.ImplicitDict) specification for how to create the resource.
        :param resource_origin: The location where this resource originated.
        :param dependencies: If this resource depends on any other resources, each of the other dependencies should be declared as an additional typed parameter to the constructor.  Each parameter type should be a class that is a subclass of Resource.
        """
        self.resource_origin = resource_origin

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
    resource_declarations: Dict[ResourceID, ResourceDeclaration],
    resource_source: str,
    stop_when_not_created: bool = False,
) -> Dict[ResourceID, ResourceType]:
    """Instantiate all resources from the provided declarations.

    Note that some declarations, such as resources whose specifications contain ExternalFiles, may be mutated while the
    resource is loaded.

    Args:
        resource_declarations: Mapping between resource ID and declaration for that resource.
        resource_source: Where this set of resource declarations originate.
        stop_when_not_created: If true, reraise any MissingResourceErrors encountered while creating resources.

    Returns: Mapping between resource ID and an instance of that declared resource.
    """
    resource_pool: Dict[ResourceID, ResourceType] = {}
    could_not_create: Set[ResourceID] = set()

    resources_created = 1
    unmet_dependencies_by_resource = {}
    while resources_created > 0:
        resources_created = 0
        for name, declaration in resource_declarations.items():
            # Check if we've already tried to create this resource
            if name in resource_pool or name in could_not_create:
                continue

            # Check if we've already tried to create all dependencies
            unmet_dependencies = [
                d
                for d in declaration.dependencies.values()
                if d not in resource_pool and d not in could_not_create
            ]
            if unmet_dependencies:
                unmet_dependencies_by_resource[name] = unmet_dependencies
                continue  # Try again next loop iteration, hopefully with more dependencies met

            # Check if this resource depends on any resources that could not be created
            uncreated_dependencies = [
                d for d in declaration.dependencies.values() if d in could_not_create
            ]
            if uncreated_dependencies:
                logger.warning(
                    f"Could not create resource `{name}` because it depends on resources that could not be created: {', '.join(uncreated_dependencies)}"
                )
                could_not_create.add(name)
                continue

            # All dependencies met; try to create resource
            try:
                resource_origin = f"{name} in {resource_source}"
                resource_pool[name] = _make_resource(
                    declaration, resource_pool, resource_origin
                )
                resources_created += 1
            except MissingResourceError as e:
                logger.warning(f"Could not create resource `{name}` because {e}")
                if stop_when_not_created:
                    raise e
                could_not_create.add(name)

    if len(resource_pool) + len(could_not_create) != len(resource_declarations):
        uncreated_resources = [
            (r + " ({} missing)".format(", ".join(unmet_dependencies_by_resource[r])))
            for r in resource_declarations
            if r not in resource_pool and r not in could_not_create
        ]
        raise ValueError(
            f"Could not create resources: {', '.join(uncreated_resources)} (do you have circular dependencies?)"
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
        if arg_name == "resource_origin":
            continue
        if arg_name == "specification":
            specification_type = arg_type
            continue
        if arg_name not in declaration.dependencies:
            raise ValueError(
                f'Resource declaration for {declaration.resource_type} is missing a source for dependency "{arg_name}" ({arg_type.__name__})'
            )

    return resource_type, specification_type


def _make_resource(
    declaration: ResourceDeclaration,
    resource_pool: Dict[ResourceID, Resource],
    resource_origin: str,
) -> Resource:
    resource_type, specification_type = get_resource_types(declaration)

    constructor_args = {"resource_origin": resource_origin}
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

    resource = resource_type(**constructor_args)
    return resource


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
