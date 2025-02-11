import re
from typing import Dict, List, Optional

from implicitdict import ImplicitDict

from monitoring.monitorlib.fetch import Query
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

    access_tokens: Optional[List[AccessTokenIdentifier]]
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

    def attribute_query(self, query: Query) -> None:
        claims = query.request.token
        if "error" in claims and len(claims) == 1:
            claims = None

        for participant_id, identifiers in self.identifiers.items():
            attribute_to_participant = False

            if "astm_url_regexes" in identifiers and identifiers.astm_url_regexes:
                for url_regex in identifiers.astm_url_regexes:
                    if re.fullmatch(url_regex, query.request.url):
                        attribute_to_participant = True

            if "access_tokens" in identifiers and identifiers.access_tokens:
                for access_token_identifier in identifiers.access_tokens:
                    if (
                        "issuer" in access_token_identifier
                        and access_token_identifier.issuer
                        and access_token_identifier.issuer != claims["iss"]
                    ):
                        continue
                    if (
                        "subject" in access_token_identifier
                        and access_token_identifier.subject
                        and access_token_identifier.subject != claims["sub"]
                    ):
                        continue
                    attribute_to_participant = True

            if attribute_to_participant:
                query.participant_id = participant_id
