from implicitdict import ImplicitDict

from monitoring.monitorlib.infrastructure import AuthAdapter
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.resource import Resource


class ClientIdentitySpecification(ImplicitDict):
    """
    Specification for a Client Identity resource:

    defines the audience and scope to use when a token is requested with the sole goal of
    discovering the identity under which the client is known to the DSS, and no other audience or scope
    are otherwise available in the context.

    This is mostly useful for determining the client identity upon setup of the qualifier, when no
    requests have yet been made to the DSS.
    """

    whoami_audience: str
    """Audience to request for the access token used to determine subscriber identity."""

    whoami_scope: str
    """Scope to request for the access token used to determine subscribe identity.  Must be a scope that the client is
    authorized to obtain."""


class ClientIdentityResource(Resource[ClientIdentitySpecification]):

    specification: ClientIdentitySpecification

    _adapter: AuthAdapter

    def __init__(
        self,
        specification: ClientIdentitySpecification,
        auth_adapter: AuthAdapterResource,
    ):
        self.specification = specification
        # Keep the adapter: we will only use it later at the moment it is required
        self._adapter = auth_adapter.adapter

    def subscriber(self) -> str:
        """
        Return the subscriber identity as determined by the adapter:
        this will usually only trigger a token request if no token had been requested yet by the auth adapter.

        This is a function and not a field, to possibly profit from a token that would have been requested earlier
        """

        sub = self._adapter.get_sub()
        if sub is None:
            # sub might be none because no authentication has happened yet:
            # we force one using the client identify audience and scopes

            # Trigger a caching initial token request so that adapter.get_sub() will return something
            headers = self._adapter.get_headers(
                f"https://{self.specification.whoami_audience}",
                [self.specification.whoami_scope],
            )

            sub = self._adapter.get_sub()
            # Confirm we have a `sub` field available: if we don't, we bail
            if sub is None:
                raise ValueError(
                    f"subscriber is None, meaning `sub` claim was not found in payload of token, "
                    f"using {type(self._adapter).__name__} requesting {self.specification.whoami_scope} scope "
                    f"for {self.specification.whoami_audience} audience: {headers['Authorization'][len('Bearer: '):]}"
                )

        return sub
