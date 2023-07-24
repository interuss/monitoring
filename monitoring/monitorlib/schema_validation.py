import os.path
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict

import bc_jsonpath_ng
import jsonschema.validators
import yaml


class F3411_19(str, Enum):
    OpenAPIPath = "interfaces/rid/v1/remoteid/augmented.yaml"
    GetFlightsResponse = "components.schemas.GetFlightsResponse"
    GetFlightDetailsResponse = "components.schemas.GetFlightDetailsResponse"
    PutIdentificationServiceAreaResponse = (
        "components.schemas.PutIdentificationServiceAreaResponse"
    )


class F3411_22a(str, Enum):
    OpenAPIPath = "interfaces/rid/v2/remoteid/updated.yaml"
    GetFlightsResponse = "components.schemas.GetFlightsResponse"
    GetFlightDetailsResponse = "components.schemas.GetFlightDetailsResponse"
    PutIdentificationServiceAreaResponse = (
        "components.schemas.PutIdentificationServiceAreaResponse"
    )


class F3548_21(str, Enum):
    OpenAPIPath = "interfaces/astm-utm/Protocol/utm.yaml"
    GetOperationalIntentDetailsResponse = (
        "components.schemas.GetOperationalIntentDetailsResponse"
    )


_openapi_content_cache: Dict[str, dict] = {}


def _get_openapi_content(openapi_path: str) -> dict:
    if openapi_path not in _openapi_content_cache:
        with open(openapi_path, "r") as f:
            _openapi_content_cache[openapi_path] = yaml.full_load(f)
    return _openapi_content_cache[openapi_path]


@dataclass
class ValidationError(object):
    """Error encountered while validating an instance against a schema."""

    message: str
    """Validation error message."""

    json_path: str
    """Location of the data causing the validation error."""


def _collect_errors(e: jsonschema.ValidationError) -> List[ValidationError]:
    if e.context:
        result = []
        for child in e.context:
            result.extend(_collect_errors(child))
        return result
    else:
        return [ValidationError(message=e.message, json_path=e.json_path)]


def validate(
    openapi_path: str, object_path: str, instance: dict
) -> List[ValidationError]:
    """Validate an object instance against the OpenAPI schema definition for that object type.

    Args:
        openapi_path: Path to OpenAPI file, relative to repository root.
        object_path: JSONPath to object schema within OpenAPI file content.
        instance: Instance to validate against schema.

    Returns: List of ValidationErrors (or empty list when validation passes).
    """
    base_path = os.path.split(openapi_path)[0]
    if not os.path.isabs(base_path):
        repo_root = os.path.realpath(os.path.join(os.path.split(__file__)[0], "../.."))
        base_path = os.path.join(repo_root, base_path)
    openapi_path = os.path.join(base_path, os.path.split(openapi_path)[1])
    openapi_content = _get_openapi_content(openapi_path)
    resolver = jsonschema.validators.RefResolver(
        base_uri=f"{Path(base_path).as_uri()}/", referrer=openapi_content
    )
    schema_matches = bc_jsonpath_ng.parse(object_path).find(openapi_content)
    if len(schema_matches) != 1:
        raise ValueError(
            f"Found {len(schema_matches)} matches to JSON path '{object_path}' within OpenAPI definition at {openapi_path} when expecting exactly 1 match"
        )
    schema = schema_matches[0].value

    openapi_version = openapi_content["openapi"]
    if openapi_version.startswith("3.0"):
        # https://github.com/OAI/OpenAPI-Specification/blob/main/schemas/v3.0/schema.json#L3
        validator_class = jsonschema.Draft4Validator
    elif openapi_version.startswith("3.1"):
        # https://github.com/OAI/OpenAPI-Specification/blob/main/schemas/v3.1/schema.json#L3
        validator_class = jsonschema.Draft202012Validator
    else:
        raise NotImplementedError(
            f"Cannot determine which JSON Schema validator to use for OpenAPI version {openapi_version} in {openapi_path}"
        )

    validator_class.check_schema(schema)
    validator = validator_class(schema, resolver=resolver)
    result = []
    for e in validator.iter_errors(instance):
        result.extend(_collect_errors(e))
    return result
