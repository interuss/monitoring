from datetime import datetime, timezone

import jwt

from monitoring.monitorlib.auth import AccessTokenError
from monitoring.monitorlib.auth_validation import fix_key
from monitoring.uss_qualifier.resources.communications.access_token_expectations import (
    AccessTokensExpectationsResource,
    ClaimValuePair,
)
from monitoring.uss_qualifier.resources.communications.auth_adapter import (
    AuthAdapterResource,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class GetAccessTokens(TestScenario):
    """Test scenario that retrieves and validates access tokens using an auth adapter and defined expectations."""

    def __init__(
        self,
        auth_adapter: AuthAdapterResource,
        expectations: AccessTokensExpectationsResource,
    ):
        super().__init__()
        self._auth_adapter = auth_adapter
        self._expectations = expectations

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.begin_test_case("Validate access tokens")

        participants = (
            [self._auth_adapter.participant_id]
            if self._auth_adapter.participant_id
            else []
        )

        for expect in self._expectations.spec.expectations:
            # 1. Retrieve the access token and validate structural integrity as a JWT.
            self.begin_test_step("Get access token")
            token: str | None = None
            header: dict | None = None
            payload: dict | None = None
            request_time = datetime.now(timezone.utc)

            with self.check(
                "Access token retrievable", participants=participants
            ) as check:
                try:
                    token = self._auth_adapter.adapter.issue_token(
                        expect.request.intended_audience, expect.request.scopes
                    )
                    # Extract header and payload without signature validation to confirm structure.
                    header = jwt.get_unverified_header(token)
                    payload = jwt.decode(token, options={"verify_signature": False})
                except AccessTokenError as e:
                    check.record_failed(
                        summary="Failed to retrieve access token from authorization source",
                        details=str(e),
                    )
                except jwt.DecodeError as e:
                    check.record_failed(
                        summary="Retrieved access token is not a well-formed JWT",
                        details=f"Token string could not be decoded as a JSON Web Token: {str(e)}",
                    )
                except Exception as e:
                    check.record_failed(
                        summary="Unexpected error encountered while obtaining or parsing access token",
                        details=str(e),
                    )

            self.end_test_step()

            # 2. Evaluate all defined token characteristics and cryptographic expectations.
            if token and header and payload:
                self.begin_test_step("Validate access token")

                # --- Token Header Algorithm Expectation ---
                if "alg" in expect.expectations and expect.expectations.alg:
                    with self.check(
                        "Token header algorithm", participants=participants
                    ) as check:
                        actual_alg = header.get("alg")
                        if actual_alg != expect.expectations.alg:
                            check.record_failed(
                                summary="JWT 'alg' header claim does not match expectation",
                                details=f"Expected algorithm: '{expect.expectations.alg}', Observed algorithm in JWT header: '{actual_alg}'.",
                            )

                # --- Token Header Values Expectation ---
                if "has_header_values" in expect.expectations and expect.expectations.has_header_values:
                    with self.check(
                        "Token header value", participants=participants
                    ) as check:
                        failures = self._evaluate_claims(
                            header, expect.expectations.has_header_values
                        )
                        if failures:
                            check.record_failed(
                                summary="One or more JWT header key-value assertions failed",
                                details="\n".join(failures),
                            )

                # --- Cryptographic Signature Validation Expectation ---
                if "validates_against_public_key" in expect.expectations and expect.expectations.validates_against_public_key:
                    with self.check(
                        "Token signature validates against public key",
                        participants=participants,
                    ) as check:
                        try:
                            public_pem = fix_key(
                                expect.expectations.validates_against_public_key
                            )
                            # Perform signature verification while intentionally bypassing audience/timestamp checks
                            # to isolate signature evaluation and prevent false positives from expired/immature tokens.
                            jwt.decode(
                                token,
                                key=public_pem,
                                algorithms=[header.get("alg", "RS256")],
                                options={
                                    "verify_signature": True,
                                    "verify_aud": False,
                                    "verify_exp": False,
                                    "verify_nbf": False,
                                    "verify_iss": False,
                                },
                            )
                        except jwt.InvalidTokenError as e:
                            check.record_failed(
                                summary="Access token cryptographic signature validation failed",
                                details=str(e),
                            )
                        except Exception as e:
                            check.record_failed(
                                summary="Failed to load public validation key or verify token signature",
                                details=str(e),
                            )

                # --- Expiration Duration 'More Than' Expectation ---
                if "expires_in_more_than" in expect.expectations and expect.expectations.expires_in_more_than:
                    with self.check(
                        "Token expiration duration longer than",
                        participants=participants,
                    ) as check:
                        exp = payload.get("exp")
                        if exp is None or not isinstance(exp, (int, float)):
                            check.record_failed(
                                summary="JWT payload is missing a valid numeric 'exp' claim",
                                details=f"Observed 'exp' in payload: {exp}",
                            )
                        else:
                            exp_datetime = datetime.fromtimestamp(exp, timezone.utc)
                            min_exp_datetime = (
                                request_time
                                + expect.expectations.expires_in_more_than.timedelta
                            )
                            if exp_datetime < min_exp_datetime:
                                check.record_failed(
                                    summary="Access token expiration ('exp') is not sufficiently far in the future",
                                    details=(
                                        f"Token Request Time: {request_time}\n"
                                        f"Minimum required offset: {expect.expectations.expires_in_more_than}\n"
                                        f"Earliest allowed 'exp' timestamp: {min_exp_datetime}\n"
                                        f"Observed 'exp' claim: {exp_datetime} (Delta remaining: {exp_datetime - request_time})"
                                    ),
                                )

                # --- Expiration Duration 'Less Than' Expectation ---
                if "expires_in_less_than" in expect.expectations and expect.expectations.expires_in_less_than:
                    with self.check(
                        "Token expiration duration shorter than",
                        participants=participants,
                    ) as check:
                        exp = payload.get("exp")
                        if exp is None or not isinstance(exp, (int, float)):
                            check.record_failed(
                                summary="JWT payload is missing a valid numeric 'exp' claim",
                                details=f"Observed 'exp' in payload: {exp}",
                            )
                        else:
                            exp_datetime = datetime.fromtimestamp(exp, timezone.utc)
                            max_exp_datetime = (
                                request_time
                                + expect.expectations.expires_in_less_than.timedelta
                            )
                            if exp_datetime > max_exp_datetime:
                                check.record_failed(
                                    summary="Access token expiration ('exp') exceeds the maximum allowed future duration",
                                    details=(
                                        f"Token Request Time: {request_time}\n"
                                        f"Maximum permitted offset: {expect.expectations.expires_in_less_than}\n"
                                        f"Latest allowed 'exp' timestamp: {max_exp_datetime}\n"
                                        f"Observed 'exp' claim: {exp_datetime} (Delta remaining: {exp_datetime - request_time})"
                                    ),
                                )

                # --- Token Payload Claim Values Expectation ---
                if "has_claim_values" in expect.expectations and expect.expectations.has_claim_values:
                    with self.check(
                        "Token payload claim value", participants=participants
                    ) as check:
                        failures = self._evaluate_claims(
                            payload, expect.expectations.has_claim_values
                        )
                        if failures:
                            check.record_failed(
                                summary="One or more JWT payload claim assertions failed",
                                details="\n".join(failures),
                            )

                self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _evaluate_claims(
        self, dictionary: dict, expectations: list[ClaimValuePair]
    ) -> list[str]:
        """Evaluates a dictionary against a set of ClaimValuePair expectations.

        Returns:
            A list of string descriptions detailing any failed expectations. An empty list signifies success.
        """
        failures: list[str] = []
        for pair in expectations:
            claim_name = pair.claim
            if claim_name not in dictionary:
                failures.append(
                    f"Required claim '{claim_name}' is entirely absent from the dictionary."
                )
                continue

            actual_val = dictionary[claim_name]

            if "equals_string_value" in pair and pair.equals_string_value is not None:
                if not isinstance(actual_val, str):
                    failures.append(
                        f"Claim '{claim_name}' expected to be of type 'str', but observed type '{type(actual_val).__name__}'."
                    )
                elif actual_val != pair.equals_string_value:
                    failures.append(
                        f"Claim '{claim_name}': Expected string value '{pair.equals_string_value}', but observed '{actual_val}'."
                    )

            if "equals_number_value" in pair and pair.equals_number_value is not None:
                if not isinstance(actual_val, (int, float)):
                    failures.append(
                        f"Claim '{claim_name}' expected to be numeric, but observed type '{type(actual_val).__name__}'."
                    )
                elif actual_val != pair.equals_number_value:
                    failures.append(
                        f"Claim '{claim_name}': Expected numeric value {pair.equals_number_value}, but observed {actual_val}."
                    )

        return failures
