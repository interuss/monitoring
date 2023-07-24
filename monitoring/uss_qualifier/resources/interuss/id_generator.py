from implicitdict import ImplicitDict
import jwt

from monitoring.prober.infrastructure import IDFactory
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.resource import Resource


class IDGeneratorSpecification(ImplicitDict):
    """Generated IDs contain the client's identity so the appropriate client can clean up any dangling resources.
    To determine the client's identity, an access token is retrieved and the subscriber is read from the obtained token.
    Therefore, the client running uss_qualifier must have the ability to obtain an access token via an auth adapter.
    """

    example_audience: str
    """Audience to request for the access token used to determine subscriber identity."""

    example_scope: str
    """Scope to request for the access token used to determine subscribe identity.  Must be a scope that the client is
    authorized to obtain."""


class IDGeneratorResource(Resource[IDGeneratorSpecification]):
    id_factory: IDFactory

    def __init__(
        self,
        specification: IDGeneratorSpecification,
        auth_adapter: AuthAdapterResource,
    ):
        token = auth_adapter.adapter.issue_token(
            specification.example_audience, [specification.example_scope]
        )
        payload = jwt.decode(token, options={"verify_signature": False})
        if "sub" not in payload:
            raise ValueError(
                f"`sub` claim not found in payload of token using {type(auth_adapter).__name__} requesting {specification.example_scope} scope for {specification.example_audience} audience: {token}"
            )
        subscriber = payload["sub"]
        self.id_factory = IDFactory(subscriber)
