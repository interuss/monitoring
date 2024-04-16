from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib import fetch, schema_validation
from monitoring.monitorlib.auth import InvalidTokenSignatureAuth
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.schema_validation import F3548_21
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class GenericAuthValidator:
    """
    Utility class for common DSS authentication validation requirements.
    """

    def __init__(
        self,
        scenario: TestScenario,
        dss: DSSInstance,
        valid_scope: Scope,
    ):
        self._pid = dss.participant_id
        self._scenario = scenario
        self._authenticated_session = dss.client
        self._invalid_token_session = UTMClientSession(
            dss.base_url, auth_adapter=InvalidTokenSignatureAuth()
        )
        self._no_auth_session = UTMClientSession(dss.base_url, auth_adapter=None)
        self._valid_scope = valid_scope

    def query_no_auth(self, **query_kwargs) -> fetch.Query:
        """Issue a query to the DSS without any credentials being passed"""
        q = fetch.query_and_describe(client=self._no_auth_session, **query_kwargs)
        self._scenario.record_query(q)
        return q

    def query_invalid_token(self, **query_kwargs) -> fetch.Query:
        """
        Issue a query to the DSS with an invalid token signature, but a valid token.
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
        Issue a query to the DSS with a valid token, but omits specifying a scope.
        """
        q = fetch.query_and_describe(client=self._authenticated_session, **query_kwargs)
        self._scenario.record_query(q)
        return q

    def query_wrong_scope(self, scope: str, **query_kwargs) -> fetch.Query:
        """
        Issue a query to the DSS with a valid token, but with a scope that is not allowed
        to perform the operation.
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
        Issue a query to the DSS with valid credentials.
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

        with self._scenario.check(
            "Unauthorized requests return the proper error message body", self._pid
        ) as check:
            errors = schema_validation.validate(
                F3548_21.OpenAPIPath,
                F3548_21.ErrorResponse,
                q.response.json,
            )
            if errors:
                check.record_failed(
                    summary="Unexpected error response body",
                    details=f"Response body for {q.request.method} query to {q.request.url} failed validation: {errors}, "
                    f"body content was: {q.response.json}",
                    query_timestamps=[q.request.timestamp],
                )
