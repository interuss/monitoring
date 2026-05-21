import re

from implicitdict import ImplicitDict, Optional
from loguru import logger

from monitoring.monitorlib.fetch import Query, QueryType
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.resource import Resource


class AccessTokenIdentifier(ImplicitDict):
    issuer: Optional[str]
    """If specified, this identifier only applies to access tokens from this issuer.  If not specified, this identifier applies to any access token."""

    subject: Optional[str]
    """If specified, assume the participant is responsible for applicable access tokens containing this subject."""


class USSIdentifiers(ImplicitDict):
    server_url_regexes: Optional[list[str]]
    """If a URL to an endpoint matches one of these regular expressions, assume the participant is responsible for that server"""

    access_tokens: Optional[list[AccessTokenIdentifier]]
    """If an access token matches one of these identifiers, assume the participant is responsible for that access token"""

    def matches_server_url(self, url: str) -> bool:
        if "server_url_regexes" in self and self.server_url_regexes:
            for url_regex in self.server_url_regexes:
                if re.fullmatch(url_regex, url):
                    return True
        return False


class USSIdentificationSpecification(ImplicitDict):
    uss_identifiers: dict[ParticipantID, USSIdentifiers]
    """For each specified participant, a set of information that allows actions, resources, etc to be associated with that participant."""


class USSIdentificationResource(Resource[USSIdentificationSpecification]):
    identifiers: dict[ParticipantID, USSIdentifiers]
    """"For each specified participant, a set of information that allows actions, resources, etc to be associated with that participant.  Guaranteed not None."""

    def __init__(
        self,
        specification: USSIdentificationSpecification,
        resource_origin: str,
    ):
        super().__init__(specification, resource_origin)
        self.identifiers = specification.uss_identifiers or {}

    def attribute_query_server(self, query: Query) -> None:
        """Identify the participant ID of the server responding to this query and mutate `query` accordingly, if possible"""
        claims = query.request.token
        if "error" in claims and len(claims) == 1:
            claims = None

        for participant_id, identifiers in self.identifiers.items():
            attribute_to_participant = False

            if "server_url_regexes" in identifiers and identifiers.server_url_regexes:
                # The participant is responsible for the server end of the query when the query URL matches one of the participant's
                if identifiers.matches_server_url(query.request.url):
                    attribute_to_participant = True

            if attribute_to_participant:
                query.participant_id = participant_id

    def identify_query_client(self, query: Query) -> ParticipantID | None:
        """Identify the participant ID of the client making this query if possible"""
        claims = query.request.token
        if "error" in claims and len(claims) == 1:
            claims = None

        query_type = query.query_type if "query_type" in query else None
        if query_type == QueryType.F3411v22aUSSPostIdentificationServiceArea:
            url = (
                (query.request.json or {})
                .get("service_area", {})
                .get("uss_base_url", None)
            )
        elif query_type == QueryType.F3411v19USSPostIdentificationServiceArea:
            url = (
                (query.request.json or {})
                .get("service_area", {})
                .get("flights_url", None)
            )
        elif query_type == QueryType.F3548v21USSNotifyOperationalIntentDetailsChanged:
            url = (
                (query.request.json or {})
                .get("operational_intent", {})
                .get("reference", {})
                .get("uss_base_url", None)
            )
        elif query_type == QueryType.F3548v21USSNotifyConstraintDetailsChanged:
            url = (
                (query.request.json or {})
                .get("constraint", {})
                .get("reference", {})
                .get("uss_base_url", None)
            )
        else:
            url = None

        matching_participants = []
        for participant_id, identifiers in self.identifiers.items():
            attribute_to_participant = False

            if "server_url_regexes" in identifiers and identifiers.server_url_regexes:
                # The participant is responsible for the client end of the query when the request body is a payload specifying a callback server operated by the participant
                if url and identifiers.matches_server_url(url):
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
                matching_participants.append(participant_id)

        if len(matching_participants) == 1:
            return matching_participants[0]
        elif len(matching_participants) > 1:
            logger.warning(
                "Multiple participants {} match as clients for query {} {}",
                ", ".join(matching_participants),
                query.request.method,
                query.request.url,
            )
        return None
