from implicitdict import ImplicitDict
from loguru import logger

from monitoring.benchmarker.configurations.configuration import (
    BenchmarkConfiguration,
)
from monitoring.monitorlib.schema_validation import (
    ValidationError,
    validate_implicitdict_object,
)
from monitoring.uss_qualifier.fileio import load_dict_with_references
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


def load_config(
    config_name: str, skip_validation: bool = False
) -> BenchmarkConfiguration:
    """Load, optionally validate, and parse a benchmark configuration file reference.

    Args:
        config_name: Configuration string indicating file reference (e.g. file://path/to/config.jsonnet)
        skip_validation: Whether to skip schema validation of the configuration.

    Returns: Parsed BenchmarkConfiguration instance.
    """
    config_src = load_dict_with_references(config_name)

    if not skip_validation:
        logger.info("Validating configuration...")
        validation_errors = validate_config(config_src)
        if validation_errors:
            for e in validation_errors:
                logger.error("[{}]: {}", e.json_path, e.message)
            raise ValueError(
                f"{len(validation_errors)} benchmark configuration validation errors indicated above.  Hint: resolve the clearest error first and then rerun validation."
            )

    return ImplicitDict.parse(config_src, BenchmarkConfiguration)
