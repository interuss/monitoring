from typing import Optional, List, Dict

from implicitdict import ImplicitDict

from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.resource import Resource


class AccessTokenIdentifier(ImplicitDict):
    issuer: Optional[str]
    """If specified, this identifier only applies to access tokens from this issuer.  If not specified, this identifier applies to any access token."""

    subject: Optional[str]
    """If specified, assume the participant is responsible for applicable access tokens containing this subject."""


class USSIdentifiers(ImplicitDict):
    astm_url_regexes: Optional[List[str]]
    """If a URL to an ASTM (F3411, F3548, etc) endpoint matches one of these regular expressions, assume the participant is responsible for that server"""

    access_tokens: Optional[List[str]]
    """If an access token matches one of these identifiers, assume the participant is responsible for that access token"""


class USSIdentificationSpecification(ImplicitDict):
    uss_identifiers: Dict[ParticipantID, USSIdentifiers]
    """For each specified participant, a set of information that allows actions, resources, etc to be associated with that participant."""


class USSIdentificationResource(Resource[USSIdentificationSpecification]):
    identifiers: Dict[ParticipantID, USSIdentifiers]
    """"For each specified participant, a set of information that allows actions, resources, etc to be associated with that participant.  Guaranteed not None."""

    def __init__(
        self,
        specification: USSIdentificationSpecification,
        resource_origin: str,
    ):
        super(USSIdentificationResource, self).__init__(specification, resource_origin)
        self.identifiers = specification.uss_identifiers or {}
