from typing import Optional

from implicitdict import ImplicitDict, StringBasedTimeDelta

from monitoring.uss_qualifier.resources.resource import Resource


class AccessTokenRequest(ImplicitDict):
    intended_audience: str
    scopes: list[str]


class ClaimValuePair(ImplicitDict):
    claim: str
    """The JWT claim that is expected to have a particular value."""

    equals_string_value: Optional[str]
    """The claim value is this string."""

    equals_number_value: Optional[float]
    """The claim value is this number."""


class Expectations(ImplicitDict):
    alg: Optional[str]
    """JWT `alg` header value must match this value (e.g., RS256)."""

    has_header_values: Optional[list[ClaimValuePair]]
    """Particular keys in the header satisfy these criteria."""

    validates_against_public_key: Optional[str]
    """Access token signature should validate against this public key.
    
    Can be a literal public key, or an http(s) URL pointing to a JWKS .json file, or a local PEM file; see fix_key in auth_validation.py."""

    expires_in_more_than: Optional[StringBasedTimeDelta]
    """The `exp` claim should be further in the future than the request time plus this delta."""

    expires_in_less_than: Optional[StringBasedTimeDelta]
    """The `exp` claim should be prior to the request time plus this delta."""

    has_claim_values: Optional[list[ClaimValuePair]]
    """Particular keys in the payload satisfy these criteria."""


class AccessTokenExpectations(ImplicitDict):
    request: AccessTokenRequest
    """A token requested in this way..."""

    expectations: Expectations
    """...has these expectations."""


class AccessTokensExpectationsSpecification(ImplicitDict):
    expectations: list[AccessTokenExpectations]


class AccessTokensExpectationsResource(Resource[AccessTokensExpectationsSpecification]):
    pass

    def __init__(
        self,
        specification: AccessTokensExpectationsSpecification,
        resource_origin: str,
        **dependencies,
    ):
        self.spec = specification
        super().__init__(specification, resource_origin, **dependencies)
