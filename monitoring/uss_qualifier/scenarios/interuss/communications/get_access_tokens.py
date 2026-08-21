from datetime import UTC, datetime
from typing import Optional

import jwt

from monitoring.monitorlib.auth import AccessTokenError
from monitoring.monitorlib.auth_validation import fix_key
from monitoring.monitorlib.inspection import evaluate_attributes, fullname
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.communications.access_token_expectations import (
    AccessTokensExpectationsResource,
    ClaimValuePair,
)
from monitoring.uss_qualifier.resources.communications.auth_adapter import (
    AuthAdapterExpectationsResource,
    AuthAdapterResource,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class GetAccessTokens(TestScenario):
    """Test scenario that retrieves and validates access tokens using an auth adapter and defined expectations."""

    def __init__(
        self,
        auth_adapter: AuthAdapterResource,
        token_expectations: Optional[AccessTokensExpectationsResource] = None,
        adapter_expectations: Optional[AuthAdapterExpectationsResource] = None,
    ):
        super().__init__()
        self._auth_adapter = auth_adapter
        self._token_expectations = token_expectations
        self._adapter_expectations = adapter_expectations

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        participants = (
            [self._auth_adapter.participant_id]
            if self._auth_adapter.participant_id
            else []
        )

        self._validate_auth_adapter(participants)
        self._validate_token_expectations(participants)

        self.end_test_scenario()

    def _validate_auth_adapter(self, participants: list[ParticipantID]):
        if not self._adapter_expectations:
            return

        self.begin_test_case("Validate auth adapter")
        self.begin_test_step("Validate auth adapter characteristics")

        for expect in self._adapter_expectations.spec.expectations:
            # --- Adapter Type Expectation ---
            if "adapter_type" in expect and expect.adapter_type:
                with self.check(
                    "Auth adapter type", participants=participants
                ) as check:
                    actual_type = type(self._auth_adapter.adapter).__name__
                    actual_fullname = fullname(type(self._auth_adapter.adapter))
                    if (
                        expect.adapter_type != actual_type
                        and expect.adapter_type != actual_fullname
                    ):
                        check.record_failed(
                            summary=f"Auth adapter is of type '{actual_type}' instead of expected '{expect.adapter_type}'",
                            details=f"Expected auth adapter to be an instance of '{expect.adapter_type}', but found '{actual_fullname}' ({actual_type})",
                        )

            # --- Attribute Values Expectation ---
            if "attribute_values" in expect and expect.attribute_values:
                with self.check(
                    "Auth adapter attribute", participants=participants
                ) as check:
                    failures = evaluate_attributes(
                        self._auth_adapter.adapter, expect.attribute_values
                    )
                    if failures:
                        check.record_failed(
                            summary="One or more auth adapter attribute assertions failed",
                            details="\n".join(failures),
                        )

        self.end_test_step()
        self.end_test_case()

    def _validate_token_expectations(self, participants: list[ParticipantID]):
        if not self._token_expectations:
            return

        self.begin_test_case("Validate access tokens")

        for expect in self._token_expectations.spec.expectations:
            # 1. Retrieve the access token and validate structural integrity as a JWT.
            self.begin_test_step("Get access token")
            token: str | None = None
            header: dict | None = None
            payload: dict | None = None
            request_time = datetime.now(UTC)

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

                # --- Token Header Values Expectation ---
                if (
                    "has_header_values" in expect.expectations
                    and expect.expectations.has_header_values
                ):
                    with self.check(
                        "Token header value", participants=participants
                    ) as check:
                        failures = self._evaluate_claims(
                            header,
                            expect.expectations.has_header_values,
                            request_time,
                        )
                        if failures:
                            check.record_failed(
                                summary="One or more JWT header key-value assertions failed",
                                details="\n".join(failures),
                            )

                # --- Cryptographic Signature Validation Expectation ---
                if (
                    "validates_against_public_key" in expect.expectations
                    and expect.expectations.validates_against_public_key
                ):
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

                # --- Token Payload Claim Values Expectation ---
                if (
                    "has_claim_values" in expect.expectations
                    and expect.expectations.has_claim_values
                ):
                    with self.check(
                        "Token payload claim value", participants=participants
                    ) as check:
                        failures = self._evaluate_claims(
                            payload,
                            expect.expectations.has_claim_values,
                            request_time,
                        )
                        if failures:
                            check.record_failed(
                                summary="One or more JWT payload claim assertions failed",
                                details="\n".join(failures),
                            )

                self.end_test_step()

        self.end_test_case()

    def _evaluate_claims(
        self,
        dictionary: dict,
        expectations: list[ClaimValuePair],
        request_time: datetime,
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

            if "beyond_request_time_offset" in pair and pair.beyond_request_time_offset:
                if not isinstance(actual_val, (int, float)):
                    failures.append(
                        f"Claim '{claim_name}' expected to be numeric time, but observed type '{type(actual_val).__name__}'."
                    )
                else:
                    actual_datetime = datetime.fromtimestamp(actual_val, UTC)
                    dt_min = pair.beyond_request_time_offset.timedelta
                    dt_actual = actual_datetime - request_time
                    if dt_actual < dt_min:
                        failures.append(
                            f"Claim '{claim_name}' expected to be at least {dt_min.total_seconds() / 60:.1f} minutes past request time {request_time.timestamp()}, but was {dt_actual.total_seconds() / 60:.1f} minutes past request time at {actual_val} instead."
                        )

            if "within_request_time_offset" in pair and pair.within_request_time_offset:
                if not isinstance(actual_val, (int, float)):
                    failures.append(
                        f"Claim '{claim_name}' expected to be numeric time, but observed type '{type(actual_val).__name__}'."
                    )
                else:
                    actual_datetime = datetime.fromtimestamp(actual_val, UTC)
                    dt_max = pair.within_request_time_offset.timedelta
                    dt_actual = actual_datetime - request_time
                    if dt_actual > dt_max:
                        failures.append(
                            f"Claim '{claim_name}' expected to be more than {dt_max.total_seconds() / 60:.1f} minutes past request time {request_time.timestamp()}, but was {dt_actual.total_seconds() / 60:.1f} minutes past request time at {actual_val} instead."
                        )

        return failures
