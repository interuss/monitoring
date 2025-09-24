import json
from typing import List
from jsonschema import validate

from implicitdict import ImplicitDict, StringBasedDateTime

# from uas_standards.eurocae_ed318 import UASZoneVersion

from monitoring.uss_qualifier.resources.eurocae.ed318.source_document import (
    SourceDocument,
)
from monitoring.uss_qualifier.resources.eurocae.ed318.source_schema import (
    SourceSchema,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class SourceDataModelValidation(TestScenario):
    source_document: SourceDocument
    source_schema: SourceSchema

    def __init__(self, source_document: SourceDocument, source_schema: SourceSchema):
        super().__init__()
        self.source_document = source_document
        self.source_schema = source_schema
        
    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.record_note(
            "Document",
            f"Ready at {self.source_document.specification.url}",
        )
        self.record_note(
            "Schema",
            f"Ready at {self.source_schema.specification.url}",
        )

        self.begin_test_case("ED-318 data model compliance")
        self.begin_test_step("Valid source")

        data = None
        with self.check(
            "Valid JSON", [self.source_document.specification.url],
        ) as check:
            try:
                data = json.loads(self.source_document.raw_document)
            except json.decoder.JSONDecodeError as e:
                check.record_failed(
                    summary="Unable to deserialize the document as JSON",
                    details=str(e),
                )

        schema = None
        with self.check(
            "Valid JSON", [self.source_schema.specification.url],
        ) as check:
            try:
                schema = json.loads(self.source_schema.raw_schema)
            except json.decoder.JSONDecodeError as e:
                check.record_failed(
                    summary="Unable to deserialize the document as JSON",
                    details=str(e),
                )

        if data and schema:
            with self.check(
                "Valid schema and values", [self.source_document.specification.url]
            ) as check:
                try:
                    validate(instance=data, schema=schema)
                except ValueError as e:
                    check.record_failed(
                        summary="Invalid format error",
                        details=str(e),
                    )

        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()
