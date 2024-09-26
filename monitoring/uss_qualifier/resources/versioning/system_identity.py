from implicitdict import ImplicitDict
from monitoring.uss_qualifier.resources.resource import Resource


class SystemIdentitySpecification(ImplicitDict):
    system_identity: str
    """Identity of a system, as understood identically by the test designer and test participants."""


class SystemIdentityResource(Resource[SystemIdentitySpecification]):
    system_identity: str

    def __init__(
        self, specification: SystemIdentitySpecification, resource_origin: str
    ):
        super(SystemIdentityResource, self).__init__(specification, resource_origin)
        self.system_identity = specification.system_identity
