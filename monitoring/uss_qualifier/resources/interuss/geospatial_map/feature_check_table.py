from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.interuss.geospatial_map.definitions import (
    FeatureCheckTable,
)
from monitoring.uss_qualifier.resources.resource import Resource


class FeatureCheckTableSpecification(ImplicitDict):
    table: FeatureCheckTable


class FeatureCheckTableResource(Resource[FeatureCheckTableSpecification]):
    table: FeatureCheckTable

    def __init__(self, specification: FeatureCheckTableSpecification):
        self.table = specification.table
