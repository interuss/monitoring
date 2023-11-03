from implicitdict import ImplicitDict

from monitoring.prober.infrastructure import IDFactory
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.resource import Resource


class IDGeneratorSpecification(ImplicitDict):
    """No fields required for the ID generator"""


class IDGeneratorResource(Resource[IDGeneratorSpecification]):

    _client_identity: ClientIdentityResource

    # Not initialised before it's actually used
    _id_factory: IDFactory = None

    def __init__(
        self,
        specification: IDGeneratorSpecification,
        client_identity: ClientIdentityResource,
    ):
        self._client_identity = client_identity

    @property
    def id_factory(self) -> IDFactory:
        # Not thread safe, but the consequences here are acceptable
        if self._id_factory is None:
            self._id_factory = IDFactory(self._client_identity.subscriber())

        return self._id_factory
