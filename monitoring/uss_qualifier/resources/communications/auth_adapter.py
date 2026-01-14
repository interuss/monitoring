import os
from enum import Enum

from implicitdict import ImplicitDict, Optional

from monitoring.monitorlib import infrastructure
from monitoring.monitorlib.auth import make_auth_adapter
from monitoring.uss_qualifier.resources.resource import MissingResourceError, Resource


class AuthAdapterSpecification(ImplicitDict):
    """Specification for an AuthAdapter resource.

    Exactly one of these fields must be populated:
      * auth_spec
      * environment_variable_containing_auth_spec
    """

    auth_spec: Optional[str]
    """Literal representation of auth spec.  WARNING: Specifying this directly may cause sensitive information to be included in reports and unprotected configuration files."""

    environment_variable_containing_auth_spec: Optional[str]
    """Name of environment variable containing the auth spec.  This is the preferred method of providing the auth spec."""

    scopes_authorized: list[str]
    """List of scopes the user in the auth spec is authorized to obtain."""


class AuthAdapterResource(Resource[AuthAdapterSpecification]):
    adapter: infrastructure.AuthAdapter
    scopes: set[str]

    def __init__(self, specification: AuthAdapterSpecification, resource_origin: str):
        super().__init__(specification, resource_origin)
        if (
            "environment_variable_containing_auth_spec" in specification
            and specification.environment_variable_containing_auth_spec
        ):
            if (
                specification.environment_variable_containing_auth_spec
                not in os.environ
            ):
                raise ValueError(
                    f"Environment variable {specification.environment_variable_containing_auth_spec} could not be found"
                )
            spec = os.environ[specification.environment_variable_containing_auth_spec]
        elif "auth_spec" in specification and specification.auth_spec:
            spec = specification.auth_spec
        else:
            raise ValueError("No auth spec was declared")
        self.adapter = make_auth_adapter(spec)
        self.scopes = set(specification.scopes_authorized)

    def assert_scopes_available(
        self, scopes_required: dict[str, str], consumer_name: str
    ) -> None:
        """Raise a MissingResourceError if any of the scopes_required are not available.

        Args:
            scopes_required: Dict relating scope required to a human description of why that scope is required.
            consumer_name: Name of entity consuming/using this auth adapter with the scopes_required.

        Raises:
            * MissingResourceError, if a required scope is not available.
        """
        for scope, reason in scopes_required.items():
            if scope not in self.scopes:
                if isinstance(scope, Enum):
                    scope = scope.value
                raise MissingResourceError(
                    f"AuthAdapterResource provided to {consumer_name} is not declared (in its resource specification) as authorized to obtain scope `{scope}` which it requires to {reason}.  Update `scopes_authorized` to include `{scope}` to provide this authorization.  {len(self.scopes)} scopes currently declared as authorized for AuthAdapterResource: {', '.join(self.scopes)}",
                    "<unknown>",
                )
