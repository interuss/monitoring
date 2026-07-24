from implicitdict import ImplicitDict

from monitoring.monitorlib.schema_validation import (
    ValidationError,
    validate_implicitdict_object,
)
from monitoring.uss_qualifier.configurations.configuration import (
    USSQualifierConfiguration,
)
from monitoring.uss_qualifier.resources.definitions import ResourceDeclaration
from monitoring.uss_qualifier.resources.resource import get_resource_types


def validate_resource_declarations(
    config: dict, base_path: str
) -> list[ValidationError]:
    """Validate resource declarations located at base_path in config against their concrete specification schemas.

    Args:
        config: Raw nested dictionary containing resource declarations at base_path.
        base_path: JSON path string indicating where resource_declarations is located (e.g. '$.resources.resource_declarations').

    Returns: List of validation errors discovered across the resource declarations.
    """
    result: list[ValidationError] = []
    resource_declarations = config
    for child in base_path.split(".")[1:]:
        resource_declarations = resource_declarations.get(child, {})
    for resource_id, declaration in resource_declarations.items():
        declaration = ImplicitDict.parse(declaration, ResourceDeclaration)
        path = base_path + "." + resource_id
        try:
            _, specification_type = get_resource_types(declaration)
        except ValueError as e:
            result.append(ValidationError(message=str(e), json_path=path))
            continue
        if specification_type is not None:
            for e in validate_implicitdict_object(
                declaration.specification, specification_type
            ):
                subpath = e.json_path
                if subpath.startswith("$."):
                    subpath = subpath[2:]
                result.append(
                    ValidationError(
                        message=e.message,
                        json_path=path + ".specification." + subpath,
                    )
                )
        elif declaration.specification:
            result.append(
                ValidationError(
                    message=f"Resource type {declaration.resource_type} does not accept a specification, but one was provided",
                    json_path=path + ".specification",
                )
            )
    return result


def validate_config(config: dict) -> list[ValidationError]:
    """Validate raw data intended to be used to create a USSQualifierConfiguration.

    Args:
        config: Raw nested dict object intended to be parsed into a USSQualifierConfiguration.

    Returns: List of validation errors discovered.
    """
    result = validate_implicitdict_object(config, USSQualifierConfiguration)

    if not result:
        result.extend(
            validate_resource_declarations(
                config, "$.v1.test_run.resources.resource_declarations"
            )
        )

    return result
