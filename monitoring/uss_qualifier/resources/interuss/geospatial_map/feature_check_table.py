import json
import os

import _jsonnet
import arrow
from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.files import (
    ExternalFile,
    load_content,
    load_dict,
)
from monitoring.uss_qualifier.resources.interuss.geospatial_map.definitions import (
    FeatureCheckTable,
)
from monitoring.uss_qualifier.resources.resource import Resource


class FeatureCheckTableGenerationSpecification(ImplicitDict):
    dict_resources: dict[str, ExternalFile] | None
    """External dict-like content (.json, .yaml, .jsonnet) to load and make available to the script.
    Key defines the name of the resource accessible to the script.
    """

    jsonnet_script: ExternalFile
    """Source of Jsonnet "script" that produces a FeatureCheckTable.
    
    This converter may access resources with std.extVars("resource_name").  Also, std.extVars("now") returns the current
    datetime as an ISO string.  The return value of the Jsonnet must be an object following the FeatureCheckTable
    schema.  `import` is not allowed.  The following additional functions are available:
      * std.native("timestamp_of")(s: str) -> float
        * s: Datetime string
        * Returns: Seconds past epoch
    """


class FeatureCheckTableSpecification(ImplicitDict):
    table: FeatureCheckTable | None
    """Statically-defined feature check table"""

    generate_at_runtime: FeatureCheckTableGenerationSpecification | None
    """Generate feature check table at runtime"""


def generate_feature_check_table(
    spec: FeatureCheckTableGenerationSpecification,
) -> FeatureCheckTable:
    # Load dict resources
    if "dict_resources" in spec and spec.dict_resources:
        resources = {
            k: json.dumps(load_dict(v)) for k, v in spec.dict_resources.items()
        }
    else:
        resources = {}

    # Useful functions not included in Jsonnet
    native_callbacks = {"timestamp_of": (("s",), lambda s: arrow.get(s).timestamp())}

    # Useful variables not included in Jsonnet
    ext_vars = {"now": arrow.utcnow().isoformat()}

    # Behavior when Jsonnet attempts to import something
    def jsonnet_import_callback(folder: str, rel: str) -> tuple[str, bytes]:
        raise ValueError("Jsonnet to generate FeatureCheckTable may not use `import`")

    # Load Jsonnet "script"
    jsonnet_string = load_content(spec.jsonnet_script)

    # Run Jsonnet "script"
    file_name = os.path.split(spec.jsonnet_script.path)[-1]
    json_str = _jsonnet.evaluate_snippet(
        file_name,
        jsonnet_string,
        ext_codes=resources,
        ext_vars=ext_vars,
        import_callback=jsonnet_import_callback,
        native_callbacks=native_callbacks,  # pyright: ignore [reportArgumentType]
    )

    # Parse output into FeatureCheckTable
    dict_content = json.loads(json_str)
    return ImplicitDict.parse(dict_content, FeatureCheckTable)


class FeatureCheckTableResource(Resource[FeatureCheckTableSpecification]):
    table: FeatureCheckTable

    def __init__(
        self, specification: FeatureCheckTableSpecification, resource_origin: str
    ):
        super().__init__(specification, resource_origin)
        if "table" in specification and specification.table:
            self.table = specification.table
        elif (
            "generate_at_runtime" in specification and specification.generate_at_runtime
        ):
            self.table = generate_feature_check_table(specification.generate_at_runtime)
        else:
            raise ValueError("No means to define FeatureCheckTable was specified")
