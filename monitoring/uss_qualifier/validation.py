from typing import List

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


def validate_config(config: dict) -> List[ValidationError]:
    """Validate raw data intended to be used to create a USSQualifierConfiguration.

    Args:
        config: Raw nested dict object intended to be parsed into a USSQualifierConfiguration.

    Returns: List of validation errors discovered.
    """
    result = validate_implicitdict_object(config, USSQualifierConfiguration)

    if not result:
        base_path = "$.v1.test_run.resources.resource_declarations"
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

    return result
