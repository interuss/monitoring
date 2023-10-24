from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.interuss.flight_authorization.definitions import (
    FlightCheckTable,
)
from monitoring.uss_qualifier.resources.resource import Resource


class FlightCheckTableSpecification(ImplicitDict):
    table: FlightCheckTable


class FlightCheckTableResource(Resource[FlightCheckTableSpecification]):
    table: FlightCheckTable

    def __init__(self, specification: FlightCheckTableSpecification):
        self.table = specification.table
