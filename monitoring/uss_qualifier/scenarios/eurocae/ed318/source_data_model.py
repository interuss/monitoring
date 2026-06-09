import json
import pathlib

import referencing
from jsonschema import ValidationError, validate
from referencing.exceptions import NoSuchResource

import monitoring
from monitoring.uss_qualifier.resources.eurocae.ed318.source_document import (
    SourceDocument,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class SourceDataModelValidation(TestScenario):
    source_document: SourceDocument
    schema_registry: referencing.Registry = referencing.Registry()
    schema: dict

    def __init__(self, source_document: SourceDocument):
        super().__init__()
        self.source_document = source_document

        # create a JSON schema registry for ED318 schemas
        def retrieve_schema(uri: str) -> referencing.Resource:
            # the $ref in the schemas are relative paths, this function allows resolving them
            repo_root = pathlib.Path(str(monitoring.__file__)).parent.parent
            schema_path = repo_root / "interfaces" / "ed318" / "schema" / uri
            if not schema_path.exists():
                raise NoSuchResource(ref=str(schema_path))
            with open(schema_path) as schema:
                return referencing.Resource.from_contents(json.load(schema))

        self.schema_registry = referencing.Registry(retrieve=retrieve_schema)
        self.schema = self.schema_registry.get_or_retrieve(
            "Schema_GeoZones.json"
        ).value.contents

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.record_note(
            "Document",
            f"Ready at {self.source_document.specification.url}",
        )

        self.begin_test_case("ED-318 data model compliance")
        self.begin_test_step("Valid source")

        data = None
        with self.check(
            "Valid JSON",
            [self.source_document.specification.url],
        ) as check:
            try:
                data = json.loads(self.source_document.raw_document)
            except json.decoder.JSONDecodeError as e:
                check.record_failed(
                    summary="Unable to deserialize the document as JSON",
                    details=str(e),
                )

        if data:
            with self.check(
                "Valid schema and values", [self.source_document.specification.url]
            ) as check:
                try:
                    validate(
                        instance=data, schema=self.schema, registry=self.schema_registry
                    )
                except ValidationError as e:
                    check.record_failed(
                        summary="Invalid format error",
                        details=str(e),
                    )

        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()
