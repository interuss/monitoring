from monitoring.benchmarker.configurations.configuration import (
    BenchmarkConfiguration,
)
from monitoring.monitorlib.schema_validation import (
    ValidationError,
    validate_implicitdict_object,
)
from monitoring.uss_qualifier.validation import validate_resource_declarations


def validate_config(config: dict) -> list[ValidationError]:
    """Validate raw data intended to be used to create a BenchmarkConfiguration.

    Args:
        config: Raw nested dict object intended to be parsed into a BenchmarkConfiguration.

    Returns: List of validation errors discovered.
    """
    result = validate_implicitdict_object(config, BenchmarkConfiguration)

    if not result:
        result.extend(
            validate_resource_declarations(config, "$.resources.resource_declarations")
        )

    return result
