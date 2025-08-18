from typing import Optional

from uas_standards.astm.f3548.v21.api import (
    OPERATIONS,
    OperationID,
    SetUssAvailabilityStatusParameters,
    UssAvailabilityState,
    UssAvailabilityStatusResponse,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError, QueryType
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.scenarios.astm.utm.dss.authentication.generic import (
    GenericAuthValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import PendingCheck, TestScenario


class AvailabilityAuthValidator:
    _current_availability: Optional[UssAvailabilityStatusResponse] = None

    def __init__(
        self,
        scenario: TestScenario,
        generic_validator: GenericAuthValidator,
        dss: DSSInstance,
        test_id: str,
        no_auth_session: UTMClientSession,
        invalid_token_session: UTMClientSession,
        test_wrong_scope: Optional[str] = None,
        test_missing_scope: bool = False,
    ):
        """

        Args:
            scenario: Scenario on which the checks will be done
            generic_validator: Provides generic verification methods for DSS API calls
            dss: the DSS instance being tested
            test_id: identifier to use for the subscriptions that will be created
            no_auth_session: an unauthenticated session
            invalid_token_session: a session using a well-formed token that has an invalid signature
            test_wrong_scope: a valid scope that is not allowed to perform operations on subscriptions, if available.
                         If None, checks using a wrong scope will be skipped.
            test_missing_scope: if True, will attempt to perform operations without specifying a scope using the valid credentials.
        """
        self._scenario = scenario
        self._gen_val = generic_validator
        self._dss = dss
        self._pid = dss.participant_id
        self._test_id = test_id

        self._no_auth_session = no_auth_session
        self._invalid_token_session = invalid_token_session

        self._test_wrong_scope = test_wrong_scope
        self._test_missing_scope = test_missing_scope

    def verify_availability_endpoints_authentication(self):
        self._verify_read()
        self._verify_set()

    def _verify_read(self):
        op = OPERATIONS[OperationID.GetUssAvailability]
        query_kwargs = dict(
            verb=op.verb,
            url=op.path.format(uss_id=self._test_id),
            query_type=QueryType.F3548v21DSSGetUssAvailability,
            participant_id=self._dss.participant_id,
        )

        # No auth:
        no_auth_q = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Read availability with missing credentials", self._pid
        ) as check:
            if no_auth_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {no_auth_q.status_code}",
                    details=no_auth_q.failure_details,
                    query_timestamps=[no_auth_q.request.timestamp],
                )

        self._gen_val.verify_4xx_response(no_auth_q)

        # Bad token signature:
        invalid_token_q = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Read availability with invalid credentials", self._pid
        ) as check:
            if invalid_token_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {invalid_token_q.status_code}",
                    details=invalid_token_q.failure_details,
                    query_timestamps=[invalid_token_q.request.timestamp],
                )

        self._gen_val.verify_4xx_response(invalid_token_q)

        # Valid credentials but missing scope:
        if self._test_missing_scope:
            no_scope_q = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Read availability with missing scope", self._pid
            ) as check:
                if no_scope_q.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {no_scope_q.status_code}",
                        details=no_scope_q.failure_details,
                        query_timestamps=[no_scope_q.request.timestamp],
                    )

            self._gen_val.verify_4xx_response(no_scope_q)

        # Valid credentials but wrong scope:
        if self._test_wrong_scope:
            wrong_scope_q = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Read availability with incorrect scope", self._pid
            ) as check:
                if wrong_scope_q.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {wrong_scope_q.status_code}",
                        details=wrong_scope_q.failure_details,
                        query_timestamps=[wrong_scope_q.request.timestamp],
                    )

            self._gen_val.verify_4xx_response(wrong_scope_q)

        # Correct token:
        #  - confirms that the request would otherwise work
        request_ok = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Read availability with valid credentials", self._pid
        ) as check:
            if request_ok.status_code != 200:
                check.record_failed(
                    summary=f"Expected 200, got {request_ok.status_code}",
                    details=request_ok.failure_details,
                    query_timestamps=[request_ok.request.timestamp],
                )

        with self._scenario.check(
            "USS Availability Get response format conforms to spec", self._pid
        ) as check:
            try:
                parsed_resp = request_ok.parse_json_result(
                    UssAvailabilityStatusResponse
                )
            except QueryError as e:
                check.record_failed(
                    summary="Could not parse the response body",
                    details=f"Could not parse the response body as a UssAvailabilityStatusResponse: {e}",
                    query_timestamps=[request_ok.request.timestamp],
                )

        self._current_availability = parsed_resp

    def _verify_set(self):
        op = OPERATIONS[OperationID.SetUssAvailability]
        query_kwargs = dict(
            verb=op.verb,
            url=op.path.format(uss_id=self._test_id),
            json=SetUssAvailabilityStatusParameters(
                old_version=self._current_availability.version,
                availability=UssAvailabilityState.Down,
            ),
            query_type=QueryType.F3548v21DSSSetUssAvailability,
            participant_id=self._dss.participant_id,
        )

        # No auth:
        no_auth_q = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Set availability with missing credentials", self._pid
        ) as check:
            if no_auth_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {no_auth_q.status_code}",
                    details=no_auth_q.failure_details,
                    query_timestamps=[no_auth_q.request.timestamp],
                )

            self._sanity_check_availability_not_updated(
                check, self._current_availability
            )

        self._gen_val.verify_4xx_response(no_auth_q)

        # Bad token signature:
        invalid_token_q = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Set availability with invalid credentials", self._pid
        ) as check:
            if invalid_token_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {invalid_token_q.status_code}",
                    details=invalid_token_q.failure_details,
                    query_timestamps=[invalid_token_q.request.timestamp],
                )

            self._sanity_check_availability_not_updated(
                check, self._current_availability
            )

        self._gen_val.verify_4xx_response(invalid_token_q)

        # Valid credentials but missing scope:
        if self._test_missing_scope:
            no_scope_q = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Set availability with missing scope", self._pid
            ) as check:
                if no_scope_q.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {no_scope_q.status_code}",
                        details=no_scope_q.failure_details,
                        query_timestamps=[no_scope_q.request.timestamp],
                    )

                self._sanity_check_availability_not_updated(
                    check, self._current_availability
                )
            self._gen_val.verify_4xx_response(no_scope_q)

        # Valid credentials but wrong scope:
        if self._test_wrong_scope:
            wrong_scope_q = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Set availability with incorrect scope", self._pid
            ) as check:
                if wrong_scope_q.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {wrong_scope_q.status_code}",
                        details=wrong_scope_q.failure_details,
                        query_timestamps=[wrong_scope_q.request.timestamp],
                    )

                self._sanity_check_availability_not_updated(
                    check, self._current_availability
                )
            self._gen_val.verify_4xx_response(wrong_scope_q)

        # Correct token:
        #  - confirms that the request would otherwise work
        request_ok = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Set availability with valid credentials", self._pid
        ) as check:
            if request_ok.status_code != 200:
                check.record_failed(
                    summary=f"Expected 200, got {request_ok.status_code}",
                    details=request_ok.failure_details,
                    query_timestamps=[request_ok.request.timestamp],
                )

        with self._scenario.check(
            "USS Availability Set response format conforms to spec", self._pid
        ) as check:
            try:
                _ = request_ok.parse_json_result(UssAvailabilityStatusResponse)
            except QueryError as e:
                check.record_failed(
                    summary="Could not parse the response body",
                    details=f"Could not parse the response body as a UssAvailabilityStatusResponse: {e}",
                    query_timestamps=[request_ok.request.timestamp],
                )

    def _sanity_check_availability_not_updated(
        self, sanity_check: PendingCheck, expected: UssAvailabilityStatusResponse
    ):
        with self._scenario.check(
            "Read availability with valid credentials", self._pid
        ) as query_check:
            try:
                response, q = self._dss.get_uss_availability(
                    self._test_id, scope=Scope.AvailabilityArbitration
                )
                self._scenario.record_query(q)
            except QueryError as e:
                self._scenario.record_queries(e.queries)
                query_check.record_failed(
                    summary="Failed to query USS availability to determine if it was updated",
                    details=f"Failed to query USS availability: {e}",
                    query_timestamps=[e.queries[0].request.timestamp],
                )
                return

            if response != expected:
                sanity_check.record_failed(
                    summary="USS availability was updated",
                    details=f"Expected the USS availability to remain unchanged ({expected}), but it was updated to {response}",
                    query_timestamps=[q.request.timestamp],
                )
