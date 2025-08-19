from implicitdict import ImplicitDict

from monitoring.uss_qualifier import fileio
from monitoring.uss_qualifier.resources.resource import Resource

class SourceSchemaSpecification(ImplicitDict):
    url: str
    """Url of the ED-318 schema to verify"""


class SourceSchema(Resource[SourceSchemaSpecification]):
    specification: SourceSchemaSpecification

    raw_schema: str
    """Content of the schema"""

    def __init__(
        self, specification: SourceSchemaSpecification, resource_origin: str
    ):
        super(SourceSchema, self).__init__(specification, resource_origin)
        self.specification = specification
        self.raw_schema = fileio.load_content(specification.url)