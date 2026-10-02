import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, get_origin, get_type_hints

from implicitdict import ImplicitDict
from loguru import logger

from monitoring import uss_qualifier as uss_qualifier_module
from monitoring.monitorlib import inspection
from monitoring.monitorlib.inspection import fullname
from monitoring.monitorlib.typing import (
    ResolvedType,
    TypeAnnotation,
    collect_typevars,
    format_type_name,
    infer_typevars_from_arg,
    is_type_covariant_match,
    substitute_typevars,
)
from monitoring.uss_qualifier import resources as resources_module
from monitoring.uss_qualifier.resources.definitions import (
    ResourceDeclaration,
    ResourceID,
    ResourceTypeName,
)

SpecificationType = TypeVar("SpecificationType", bound=ImplicitDict)


_resources_module_imported = False


def _ensure_resources_imported() -> None:
    global _resources_module_imported
    if not _resources_module_imported:
        inspection.import_submodules(resources_module)
        _resources_module_imported = True


class Resource[SpecificationType: ImplicitDict](ABC):
    resource_origin: str
    """The origin of this resource (usually the resource name in the top-level resource pool for a test configuration,
    though occasionally local to a test suite, derived from another resource, default, or something else)"""

    _typevar_map: dict[TypeVar, ResolvedType] | None = None

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

    def _get_typevar_map(self) -> dict[TypeVar, ResolvedType]:
        if self._typevar_map is not None:
            return self._typevar_map
        mapping: dict[TypeVar, ResolvedType] = {}
        params: tuple[TypeVar, ...] = getattr(self.__class__, "__parameters__", ())
        if params:
            try:
                hints = get_type_hints(self.__class__.__init__)
                for arg_name, hint in hints.items():
                    if (
                        isinstance(hint, TypeVar)
                        and hint in params
                        and hasattr(self, arg_name)
                    ):
                        val: object = getattr(self, arg_name)
                        if isinstance(val, Resource):
                            mapping[hint] = val._get_type_annotation()
                        elif isinstance(val, ImplicitDict):
                            mapping[hint] = type(val)
            except Exception:
                pass
        collect_typevars(self.__class__, mapping)
        self._typevar_map = mapping
        return mapping

    def _get_type_annotation(self) -> ResolvedType:
        cls: type = self.__class__
        params: tuple[TypeVar, ...] = getattr(cls, "__parameters__", ())
        if not params:
            return cls
        typevar_map = self._get_typevar_map()
        args = tuple(typevar_map.get(p, p) for p in params)
        return cls.__class_getitem__(args[0] if len(args) == 1 else args)

    def is_or_inherits(self, resource_type: ResourceTypeName) -> bool:
        _ensure_resources_imported()
        specified_type = inspection.resolve_type_expression(
            uss_qualifier_module, resource_type
        )
        specified_origin = get_origin(specified_type) or specified_type
        if not isinstance(specified_origin, type) or not issubclass(
            specified_origin, Resource
        ):
            raise NotImplementedError(
                f"Resource type {getattr(specified_origin, '__name__', str(specified_origin))} is not a subclass of the Resource base class"
            )
        return is_type_covariant_match(
            self._get_type_annotation(), specified_type, self._get_typevar_map()
        )


class ValueResource[T: ImplicitDict](Resource[T]):
    value: T

    def __init__(self, specification: T, resource_origin: str, **dependencies):
        super().__init__(specification, resource_origin, **dependencies)
        self.value = specification


ResourceType = TypeVar("ResourceType", bound=Resource)


class SupportedKeysNotSpecifiedError(ValueError):
    """Error when a ResourceProvidingResource is asked to provide_resource_for, but the supported key(s) are not specified correctly."""

    pass


class ResourceProvidingResource[
    SpecificationType: ImplicitDict,
    ResourceType: Resource,
](Resource[SpecificationType], ABC):
    """Resource capable of spawning ResourceType resources according to a desired key, such as an index."""

    @abstractmethod
    def provide_resource_for(self, **kwargs) -> ResourceType:
        """Provide a resource corresponding with the provided key(s) (e.g., index, USS pair, etc)."""
        raise NotImplementedError()

    def _provided_resource_origin(self, key_name: str) -> str:
        """Method that should generally be used to describe the origin of a resource provided by this resource."""
        return f"Resource for {key_name} provided by {self.resource_origin}"


class MissingResourceError(ValueError):
    missing_resource_name: str

    def __init__(self, msg: str, missing_resource_name: str):
        super().__init__(msg)
        self.missing_resource_name = missing_resource_name


def create_resources[ResourceType: Resource](
    resource_declarations: dict[ResourceID, ResourceDeclaration],
    resource_source: str,
    stop_when_not_created: bool = False,
    base_resource_pool: dict[ResourceID, ResourceType] | None = None,
) -> dict[ResourceID, ResourceType]:
    """Instantiate all resources from the provided declarations.

    Note that some declarations, such as resources whose specifications contain ExternalFiles, may be mutated while the
    resource is loaded.

    Args:
        resource_declarations: Mapping between resource ID and declaration for that resource.
        resource_source: Where this set of resource declarations originate.
        stop_when_not_created: If true, reraise any MissingResourceErrors encountered while creating resources.
        base_resource_pool: Optional mapping of pre-existing resources that declared resources may depend on.

    Returns: Mapping between resource ID and an instance of that declared resource.
    """
    resource_pool: dict[ResourceID, ResourceType] = (
        dict(base_resource_pool) if base_resource_pool is not None else {}
    )
    could_not_create: set[ResourceID] = set()

    progress_made = True
    unmet_dependencies_by_resource = {}
    while progress_made:
        progress_made = False
        for name, declaration in resource_declarations.items():
            # Check if we've already tried to create this resource
            if name in resource_pool or name in could_not_create:
                continue

            # Check if we've already tried to create all dependencies
            unmet_dependencies = []
            uncreated_dependencies = []
            for d in declaration.dependencies.values():
                is_optional = d.endswith("?")
                dep_name = d[:-1] if is_optional else d
                if dep_name not in resource_pool and dep_name not in could_not_create:
                    if not is_optional or dep_name in resource_declarations:
                        unmet_dependencies.append(dep_name)
                elif dep_name in could_not_create and not is_optional:
                    uncreated_dependencies.append(dep_name)

            if unmet_dependencies:
                unmet_dependencies_by_resource[name] = unmet_dependencies
                continue  # Try again next loop iteration, hopefully with more dependencies met

            # Check if this resource depends on any resources that could not be created
            if uncreated_dependencies:
                logger.warning(
                    f"Could not create resource `{name}` because it depends on resources that could not be created: {', '.join(uncreated_dependencies)}"
                )
                could_not_create.add(name)
                progress_made = True
                continue

            # All dependencies met; try to create resource
            try:
                resource_origin = f"{name} in {resource_source}"
                resource_pool[name] = _make_resource(
                    declaration, resource_pool, resource_origin
                )
                progress_made = True
            except MissingResourceError as e:
                logger.warning(f"Could not create resource `{name}` because {e}")
                if stop_when_not_created:
                    raise e
                could_not_create.add(name)
                progress_made = True

    uncreated_resources = [
        (r + " ({} missing)".format(", ".join(unmet_dependencies_by_resource[r])))
        for r in resource_declarations
        if r not in resource_pool and r not in could_not_create
    ]
    if uncreated_resources:
        raise ValueError(
            f"Could not create resources: {', '.join(uncreated_resources)} (do you have circular dependencies?)"
        )

    return resource_pool


@dataclass
class ResourceDeclarationTypes:
    """Resolved types and constructor signature information for a ResourceDeclaration."""

    resource_type: type[Resource]
    """Concrete Resource subclass type of the declared resource."""

    specification_type: type[ImplicitDict] | None
    """Specification type for the declared resource, or None if the resource type doesn't have a specification."""

    constructor_signature: dict[str, TypeAnnotation]
    """Mapping of constructor parameter name to its type annotation with known TypeVars substituted."""

    typevar_map: dict[TypeVar, ResolvedType]
    """Mapping of bound TypeVars on the resource class hierarchy to their resolved types."""


def get_resource_types(
    declaration: ResourceDeclaration,
) -> ResourceDeclarationTypes:
    """Get the resource and specification types and constructor signature from the declaration, validating against the resource's constructor signature.

    Args:
        declaration: Resource declaration for which to obtain types

    Returns:
        ResourceDeclarationTypes containing the resolved resource class, specification class, constructor signature, and TypeVar mapping.
    """
    _ensure_resources_imported()
    resource_type, type_args = inspection.resolve_type_and_args(
        uss_qualifier_module, declaration.resource_type, Resource
    )

    typevar_map: dict[TypeVar, ResolvedType] = {}
    params: tuple[TypeVar, ...] = getattr(resource_type, "__parameters__", ())
    for param, arg in zip(params, type_args):
        if param.__bound__ is not None and not is_type_covariant_match(
            arg, param.__bound__
        ):
            raise ValueError(
                f"Type argument {format_type_name(arg)} for {resource_type.__name__} is not a subclass of {format_type_name(param.__bound__)}"
            )
        if not isinstance(arg, TypeVar):
            typevar_map[param] = arg

    collect_typevars(resource_type, typevar_map)

    raw_signature = get_type_hints(resource_type.__init__)
    constructor_signature: dict[str, TypeAnnotation] = {
        name: substitute_typevars(t, typevar_map) for name, t in raw_signature.items()
    }
    init_params = inspect.signature(resource_type.__init__).parameters

    specification_type = None
    for arg_name, arg_type in constructor_signature.items():
        if arg_name in ("return", "self", "resource_origin"):
            continue
        if arg_name == "specification":
            if isinstance(arg_type, type) and issubclass(arg_type, ImplicitDict):
                specification_type = arg_type
            continue
        param = init_params.get(arg_name)
        if param is not None and param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        has_default = param is not None and param.default is not inspect.Parameter.empty
        if arg_name not in declaration.dependencies:
            if not has_default:
                raise ValueError(
                    f'Resource declaration for {declaration.resource_type} is missing a source for dependency "{arg_name}" ({format_type_name(arg_type)})'
                )

    for arg_name, pool_source in declaration.dependencies.items():
        if pool_source.endswith("?"):
            param = init_params.get(arg_name)
            if param is None or param.default is inspect.Parameter.empty:
                raise ValueError(
                    f'Resource declaration for {declaration.resource_type} specifies optional dependency "{pool_source}" for parameter "{arg_name}", which has no default value in {resource_type.__name__}.__init__'
                )

    return ResourceDeclarationTypes(
        resource_type=resource_type,
        specification_type=specification_type,
        constructor_signature=constructor_signature,
        typevar_map=typevar_map,
    )


def _make_resource(
    declaration: ResourceDeclaration,
    resource_pool: dict[ResourceID, Resource],
    resource_origin: str,
) -> Resource:
    decl_types = get_resource_types(declaration)
    target_typevars: set[TypeVar] = set(
        getattr(decl_types.resource_type, "__parameters__", ())
    )

    dependency_args: dict[str, Resource] = {}
    for arg_name, pool_source in declaration.dependencies.items():
        is_optional = pool_source.endswith("?")
        dep_id = pool_source[:-1] if is_optional else pool_source
        if dep_id not in resource_pool:
            if is_optional:
                continue
            raise ValueError(
                f'Resource "{pool_source}" was not found in the resource pool when trying to create {declaration.resource_type} resource'
            )
        dep_resource = resource_pool[dep_id]
        expected_type = decl_types.constructor_signature.get(arg_name)
        if expected_type is not None:
            dep_type_ann = dep_resource._get_type_annotation()
            infer_typevars_from_arg(
                expected_type, dep_type_ann, target_typevars, decl_types.typevar_map
            )
            collect_typevars(decl_types.resource_type, decl_types.typevar_map)
            resolved_expected = substitute_typevars(
                expected_type, decl_types.typevar_map
            )
            if isinstance(resolved_expected, TypeVar):
                bound = resolved_expected.__bound__
                if bound is not None and not is_type_covariant_match(
                    dep_type_ann, bound, dep_resource._get_typevar_map()
                ):
                    raise ValueError(
                        f'Dependency "{arg_name}" (resource "{dep_id}" of type {fullname(dep_resource.__class__)}) for {declaration.resource_type} does not match expected bound {format_type_name(bound)}'
                    )
            elif not is_type_covariant_match(
                dep_type_ann, resolved_expected, dep_resource._get_typevar_map()
            ):
                raise ValueError(
                    f'Dependency "{arg_name}" (resource "{dep_id}" of type {fullname(dep_resource.__class__)}) for {declaration.resource_type} does not match expected type {format_type_name(resolved_expected)}'
                )
        dependency_args[arg_name] = dep_resource

    if decl_types.specification_type is not None:
        specification = ImplicitDict.parse(
            declaration.specification, decl_types.specification_type
        )
        declaration.specification = specification
        resource = decl_types.resource_type(
            specification=specification,
            resource_origin=resource_origin,
            **dependency_args,
        )
    else:
        resource = decl_types.resource_type(
            resource_origin=resource_origin,  # type: ignore[call-arg]
            **dependency_args,
        )
    resource._typevar_map = decl_types.typevar_map
    return resource


def make_child_resources[ResourceType: Resource](
    parent_resources: dict[ResourceID, ResourceType],
    child_resource_map: dict[ResourceID, ResourceID],
    subject: str,
) -> dict[ResourceID, ResourceType]:
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
