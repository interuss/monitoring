from implicitdict import ImplicitDict

from monitoring.monitorlib.locality import LocalityCode, Locality
from monitoring.uss_qualifier.resources.resource import Resource


class LocalitySpecification(ImplicitDict):
    locality_code: LocalityCode


class LocalityResource(Resource[LocalitySpecification]):
    locality_code: LocalityCode

    def __init__(self, specification: LocalitySpecification):
        # Make sure provided code is valid
        Locality.from_locale(specification.locality_code)

        self.locality_code = specification.locality_code
