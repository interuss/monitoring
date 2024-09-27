from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.interuss.flight_authorization.definitions import (
    FlightCheckTable,
)
from monitoring.uss_qualifier.resources.resource import Resource


class FlightCheckTableSpecification(ImplicitDict):
    table: FlightCheckTable


class FlightCheckTableResource(Resource[FlightCheckTableSpecification]):
    table: FlightCheckTable

    def __init__(
        self, specification: FlightCheckTableSpecification, resource_origin: str
    ):
        super(FlightCheckTableResource, self).__init__(specification, resource_origin)
        self.table = specification.table
