from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.uss_qualifier.scenarios.astm.utm.auth_validator import (
    AuthValidationTarget,
    GenericAuthValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class EndpointAuthValidator:
    """
    Verifies authentication and authorization of a single endpoint by issuing requests with
    missing credentials (expect 401), invalid credentials (expect 401), an incorrect scope
    (expect 403), and each valid scope (expect anything other than 401 or 403).

    Each rejected request is also checked for a valid ErrorResponse body.

    The calling scenario's documentation must declare these checks in the current test step:
    * "Unauthorized requests return the proper error message body"
    * "<operation_name> with missing credentials"
    * "<operation_name> with invalid credentials"
    * "<operation_name> with an incorrect scope"
    * "<operation_name> with valid credentials"
    """

    def __init__(
        self,
        scenario: TestScenario,
        operation_name: str,
        auth_target: AuthValidationTarget,
        client_scopes: set[str],
        valid_scopes: list[Scope],
        query_kwargs: dict,
    ):
        generic_validator = GenericAuthValidator(
            scenario,
            auth_target,
            valid_scopes[0],
        )
        self._scenario = scenario
        self._operation_name = operation_name
        self._generic_validator = generic_validator
        self._pid = auth_target.participant_id
        self._client_scopes = client_scopes
        self._valid_scopes = valid_scopes
        self._query_kwargs = query_kwargs

    def verify_endpoint_authentication(self):
        """Executes each auth scenario for missing, invalid, incorrectly scoped, and valid credentials"""
        self._verify_missing_credentials()
        self._verify_invalid_credentials()
        self._verify_incorrect_scope()
        for scope in self._valid_scopes:
            self._verify_valid_credentials(scope)

    def _verify_missing_credentials(self):
        query = self._generic_validator.query_no_auth(**self._query_kwargs)
        with self._scenario.check(
            f"{self._operation_name} with missing credentials",
            self._pid,
        ) as check:
            if query.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {query.status_code}",
                    details=str(query.failure_details),
                    query_timestamps=[query.request.timestamp],
                )
        self._generic_validator.verify_4xx_response(query)

    def _verify_invalid_credentials(self):
        query = self._generic_validator.query_invalid_token(**self._query_kwargs)
        with self._scenario.check(
            f"{self._operation_name} with invalid credentials",
            self._pid,
        ) as check:
            if query.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {query.status_code}",
                    details=str(query.failure_details),
                    query_timestamps=[query.request.timestamp],
                )
        self._generic_validator.verify_4xx_response(query)

    def _verify_incorrect_scope(self):
        scope = self._find_incorrect_scope()
        if scope is None:
            self._scenario.record_note(
                f"{self._operation_name} incorrect scope",
                f"{self._operation_name}: no incorrect scope available; incorrect-scope check skipped",
            )
            return

        query = self._generic_validator.query_with_scope(scope, **self._query_kwargs)
        with self._scenario.check(
            f"{self._operation_name} with an incorrect scope",
            self._pid,
        ) as check:
            if query.status_code != 403:
                check.record_failed(
                    summary=f"Expected 403, got {query.status_code}",
                    details=str(query.failure_details),
                    query_timestamps=[query.request.timestamp],
                )
        self._generic_validator.verify_4xx_response(query)

    def _verify_valid_credentials(self, scope: Scope):
        if scope not in self._client_scopes:
            self._scenario.record_note(
                f"{self._operation_name} valid scope {scope.value}",
                "scope not available; valid-scope check skipped",
            )
            return

        query = self._generic_validator.query_with_scope(scope, **self._query_kwargs)
        with self._scenario.check(
            f"{self._operation_name} with valid credentials",
            self._pid,
        ) as check:
            if query.status_code in (401, 403):
                check.record_failed(
                    summary=f"Valid credentials with scope {scope.value} were rejected with {query.status_code}",
                    details=str(query.failure_details),
                    query_timestamps=[query.request.timestamp],
                )

    def _find_incorrect_scope(self) -> str | None:
        return self._find_incorrect_f3548_scope() or self._find_incorrect_other_scope()

    def _find_incorrect_f3548_scope(self) -> str | None:
        for scope in sorted(Scope):
            if scope not in self._valid_scopes and scope.value in self._client_scopes:
                return scope.value

    def _find_incorrect_other_scope(self) -> str | None:
        valid_scopes = {s.value for s in self._valid_scopes}
        for scope in sorted(self._client_scopes):
            if scope != "" and scope not in valid_scopes:
                return scope
