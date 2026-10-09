from typing import Protocol

from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib import fetch
from monitoring.monitorlib.auth import InvalidTokenSignatureAuth
from monitoring.monitorlib.infrastructure import (
    UTMClientSession,
    utm_client_session_factory,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    verify_error_response_body,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class AuthValidationTarget(Protocol):
    @property
    def participant_id(self) -> str: ...

    @property
    def base_url(self) -> str: ...

    @property
    def client(self) -> UTMClientSession: ...


class GenericAuthValidator:
    """
    Utility class for common authentication validation requirements.
    """

    def __init__(
        self,
        scenario: TestScenario,
        target: AuthValidationTarget,
        valid_scope: Scope,
    ):
        self._pid = target.participant_id
        self._scenario = scenario
        self._authenticated_session = target.client
        self._invalid_token_session = utm_client_session_factory.get_session(
            target.base_url, auth_adapter=InvalidTokenSignatureAuth()
        )
        self._no_auth_session = utm_client_session_factory.get_session(
            target.base_url, auth_adapter=None
        )
        self._valid_scope = valid_scope

    def query_no_auth(self, **query_kwargs) -> fetch.Query:
        """Issue a query to the authentication target without any credentials being passed"""
        q = fetch.query_and_describe(client=self._no_auth_session, **query_kwargs)
        self._scenario.record_query(q)
        return q

    def query_invalid_token(self, **query_kwargs) -> fetch.Query:
        """
        Issue a query to the authentication target with an invalid token signature, but a well-formed token.
        An appropriate scope is provided.
        """
        q = fetch.query_and_describe(
            client=self._invalid_token_session,
            scope=self._valid_scope,
            **query_kwargs,
        )
        self._scenario.record_query(q)
        return q

    def query_missing_scope(self, **query_kwargs) -> fetch.Query:
        """
        Issue a query to the authentication target with a valid token, but omits specifying a scope.
        """
        q = fetch.query_and_describe(client=self._authenticated_session, **query_kwargs)
        self._scenario.record_query(q)
        return q

    def query_with_scope(self, scope: str, **query_kwargs) -> fetch.Query:
        """
        Issue a query to the authentication target with a valid token for the supplied scope.
        Note that the auth adapter needs to be able to request a token with this scope.
        """
        q = fetch.query_and_describe(
            client=self._authenticated_session,
            scope=scope,
            **query_kwargs,
        )
        self._scenario.record_query(q)
        return q

    def query_valid_auth(self, **query_kwargs) -> fetch.Query:
        """
        Issue a query to the authentication target with valid credentials.
        """
        q = fetch.query_and_describe(
            client=self._authenticated_session,
            scope=self._valid_scope,
            **query_kwargs,
        )
        self._scenario.record_query(q)
        return q

    def verify_4xx_response(self, q: fetch.Query):
        """Verifies that the passed query response's body is a valid ErrorResponse, as per the OpenAPI spec."""
        verify_error_response_body(
            self._scenario,
            "Unauthorized requests return the proper error message body",
            self._pid,
            q,
        )
