from datetime import datetime, timedelta

from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.astm.f3548.v21.api import (
    OPERATIONS,
    ChangeConstraintReferenceResponse,
    OperationID,
    PutConstraintReferenceParameters,
    QueryConstraintReferenceParameters,
    QueryConstraintReferencesResponse,
    Time,
)

from monitoring.monitorlib import fetch
from monitoring.monitorlib.fetch import QueryError, QueryType
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.uss_qualifier.resources import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.scenarios.astm.utm.dss.authentication.generic import (
    GenericAuthValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import PendingCheck, TestScenario

TIME_TOLERANCE_SEC = 1


class ConstraintRefAuthValidator:
    def __init__(
        self,
        scenario: TestScenario,
        generic_validator: GenericAuthValidator,
        dss: DSSInstance,
        test_id: str,
        planning_area: PlanningAreaResource,
        planning_area_volume4d: Volume4D,
        no_auth_session: UTMClientSession,
        invalid_token_session: UTMClientSession,
        test_wrong_scope: str | None = None,
        test_missing_scope: bool = False,
    ):
        """

        Args:
            scenario: Scenario on which the checks will be done
            generic_validator: Provides generic verification methods for DSS API calls
            dss: the DSS instance being tested
            test_id: identifier to use for the CRs that will be created
            planning_area: the planning area to use for the subscriptions
            planning_area_volume4d: a volume 4d encompassing the planning area
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
        self._planning_area = planning_area

        time_start = datetime.now().astimezone() - timedelta(seconds=10)
        time_end = time_start + timedelta(minutes=20)

        self._cr_params = planning_area.get_new_constraint_ref_params(
            time_start=time_start,
            time_end=time_end,
        )
        self._planning_area_volume4d = planning_area_volume4d
        self._no_auth_session = no_auth_session
        self._invalid_token_session = invalid_token_session

        self._test_wrong_scope = test_wrong_scope
        self._test_missing_scope = test_missing_scope

    def verify_cr_endpoints_authentication(self):
        self._verify_cr_creation()
        self._verify_cr_get()
        self._verify_cr_mutation()
        self._verify_cr_deletion()
        self._verify_cr_search()

    def _verify_cr_creation(self):
        op = OPERATIONS[OperationID.CreateConstraintReference]
        query_kwargs = dict(
            verb=op.verb,
            url=op.path.format(entityid=self._test_id),
            json=self._cr_params,
            query_type=QueryType.F3548v21DSSCreateConstraintReference,
            participant_id=self._dss.participant_id,
        )

        # No auth
        no_auth_q = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Create constraint reference with missing credentials", self._pid
        ) as check:
            if no_auth_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {no_auth_q.status_code}",
                    query_timestamps=[no_auth_q.request.timestamp],
                )
            self._sanity_check_cr_not_created(check, no_auth_q)

        self._gen_val.verify_4xx_response(no_auth_q)

        # Invalid token
        invalid_token_q = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Create constraint reference with invalid credentials", self._pid
        ) as check:
            if invalid_token_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {invalid_token_q.status_code}",
                    query_timestamps=[invalid_token_q.request.timestamp],
                )
            self._sanity_check_cr_not_created(check, invalid_token_q)

        self._gen_val.verify_4xx_response(invalid_token_q)

        # Valid credentials but missing scope:
        if self._test_missing_scope:
            no_scope_q = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Create constraint reference with missing scope", self._pid
            ) as check:
                if no_scope_q.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {no_scope_q.status_code}",
                        query_timestamps=[no_scope_q.request.timestamp],
                    )
                self._sanity_check_cr_not_created(check, no_scope_q)

            self._gen_val.verify_4xx_response(no_scope_q)

        # Valid credentials but wrong scope:
        if self._test_wrong_scope:
            wrong_scope_q = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Create constraint reference with incorrect scope", self._pid
            ) as check:
                if wrong_scope_q.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {wrong_scope_q.status_code}",
                        query_timestamps=[wrong_scope_q.request.timestamp],
                    )
                self._sanity_check_cr_not_created(check, wrong_scope_q)

            self._gen_val.verify_4xx_response(wrong_scope_q)

        # Valid credentials
        valid_q = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Create constraint reference with valid credentials", self._pid
        ) as check:
            if valid_q.status_code != 201:  # As specified in OpenAPI spec
                check.record_failed(
                    summary=f"Expected 201, got {valid_q.status_code}",
                    details=f"Error message: {valid_q.error_message}",
                    query_timestamps=[valid_q.request.timestamp],
                )

        with self._scenario.check(
            "Create constraint reference response format conforms to spec",
            self._pid,
        ) as check:
            try:
                cr_resp = ImplicitDict.parse(
                    valid_q.response.json, ChangeConstraintReferenceResponse
                )
            except ValueError as e:
                check.record_failed(
                    summary="Could not parse the response body",
                    details=f"Failed to parse the response body as a ChangeConstraintReferenceResponse: {e}",
                    query_timestamps=[valid_q.request.timestamp],
                )

        # Save the current CR
        self._current_cr = cr_resp.constraint_reference

    def _verify_cr_get(self):
        op = OPERATIONS[OperationID.GetConstraintReference]
        query_kwargs = dict(
            verb=op.verb,
            url=op.path.format(entityid=self._test_id),
            query_type=QueryType.F3548v21DSSGetConstraintReference,
            participant_id=self._dss.participant_id,
        )

        # No Auth
        query_no_auth = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Get constraint reference with missing credentials", self._pid
        ) as check:
            if query_no_auth.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {query_no_auth.status_code}",
                    query_timestamps=[query_no_auth.request.timestamp],
                )
        self._gen_val.verify_4xx_response(query_no_auth)

        # Invalid token
        query_invalid_token = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Get constraint reference with invalid credentials", self._pid
        ) as check:
            if query_invalid_token.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {query_invalid_token.status_code}",
                    query_timestamps=[query_invalid_token.request.timestamp],
                )

        self._gen_val.verify_4xx_response(query_invalid_token)

        # Valid credentials but missing scope
        if self._test_missing_scope:
            query_missing_scope = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Get constraint reference with missing scope", self._pid
            ) as check:
                if query_missing_scope.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {query_missing_scope.status_code}",
                        query_timestamps=[query_missing_scope.request.timestamp],
                    )

            self._gen_val.verify_4xx_response(query_missing_scope)

        # Valid credentials but wrong scope
        if self._test_wrong_scope:
            query_wrong_scope = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Get constraint reference with incorrect scope", self._pid
            ) as check:
                if query_wrong_scope.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {query_wrong_scope.status_code}",
                        query_timestamps=[query_wrong_scope.request.timestamp],
                    )

            self._gen_val.verify_4xx_response(query_wrong_scope)

        # Valid credentials
        query_valid_auth = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Get constraint reference with valid credentials", self._pid
        ) as check:
            if query_valid_auth.status_code != 200:
                check.record_failed(
                    summary=f"Expected 200, got {query_valid_auth.status_code}",
                    query_timestamps=[query_valid_auth.request.timestamp],
                )

        with self._scenario.check(
            "Get constraint reference response format conforms to spec",
            self._pid,
        ) as check:
            try:
                ImplicitDict.parse(
                    query_valid_auth.response.json, ChangeConstraintReferenceResponse
                )
            except ValueError as e:
                check.record_failed(
                    summary="Could not parse the response body",
                    details=f"Failed to parse the response body as a ChangeConstraintReferenceResponse: {e}",
                    query_timestamps=[query_valid_auth.request.timestamp],
                )

    def _verify_cr_mutation(self):
        op = OPERATIONS[OperationID.UpdateConstraintReference]
        new_params = PutConstraintReferenceParameters(**self._cr_params)
        updated_volume = new_params.extents[0]
        new_end = updated_volume.time_end.value.datetime - timedelta(seconds=10)
        updated_volume.time_end = Time(value=StringBasedDateTime(new_end))
        new_params.extents = [updated_volume]
        query_kwargs = dict(
            verb=op.verb,
            url=op.path.format(entityid=self._test_id, ovn=self._current_cr.ovn),
            json=new_params,
            query_type=QueryType.F3548v21DSSUpdateConstraintReference,
            participant_id=self._dss.participant_id,
        )

        no_auth_q = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Mutate constraint reference with missing credentials", self._pid
        ) as check:
            if no_auth_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {no_auth_q.status_code}",
                    query_timestamps=[no_auth_q.request.timestamp],
                )
            self._sanity_check_cr_not_created(check, no_auth_q)

        self._gen_val.verify_4xx_response(no_auth_q)

        invalid_token_q = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Mutate constraint reference with invalid credentials", self._pid
        ) as check:
            if invalid_token_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {invalid_token_q.status_code}",
                    query_timestamps=[invalid_token_q.request.timestamp],
                )
            self._sanity_check_cr_not_updated(check, invalid_token_q)

        self._gen_val.verify_4xx_response(invalid_token_q)

        if self._test_missing_scope:
            no_scope_q = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Mutate constraint reference with missing scope", self._pid
            ) as check:
                if no_scope_q.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {no_scope_q.status_code}",
                        query_timestamps=[no_scope_q.request.timestamp],
                    )
                self._sanity_check_cr_not_updated(check, no_scope_q)

            self._gen_val.verify_4xx_response(no_scope_q)

        if self._test_wrong_scope:
            wrong_scope_q = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Mutate constraint reference with incorrect scope", self._pid
            ) as check:
                if wrong_scope_q.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {wrong_scope_q.status_code}",
                        query_timestamps=[wrong_scope_q.request.timestamp],
                    )
                self._sanity_check_cr_not_updated(check, wrong_scope_q)

            self._gen_val.verify_4xx_response(wrong_scope_q)

        valid_q = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Mutate constraint reference with valid credentials", self._pid
        ) as check:
            if valid_q.status_code != 200:
                check.record_failed(
                    summary=f"Expected 200, got {valid_q.status_code}",
                    details=f"Mutation is expected to have succeeded, but got status {valid_q.status_code} with error {valid_q.error_message} instead",
                    query_timestamps=[valid_q.request.timestamp],
                )

        with self._scenario.check(
            "Mutate constraint reference response format conforms to spec",
            self._pid,
        ) as check:
            try:
                parsed_cr = ImplicitDict.parse(
                    valid_q.response.json, ChangeConstraintReferenceResponse
                )
            except ValueError as e:
                check.record_failed(
                    summary="Could not parse the response body",
                    details=f"Failed to parse the response body as a ChangeConstraintReferenceResponse: {e}",
                    query_timestamps=[valid_q.request.timestamp],
                )

        self._current_cr = parsed_cr.constraint_reference

    def _verify_cr_deletion(self):
        op = OPERATIONS[OperationID.DeleteConstraintReference]
        query_kwargs = dict(
            verb=op.verb,
            url=op.path.format(entityid=self._test_id, ovn=self._current_cr.ovn),
            query_type=QueryType.F3548v21DSSDeleteConstraintReference,
            participant_id=self._dss.participant_id,
        )

        no_auth_q = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Delete constraint reference with missing credentials", self._pid
        ) as check:
            if no_auth_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {no_auth_q.status_code}",
                    query_timestamps=[no_auth_q.request.timestamp],
                )
        self._gen_val.verify_4xx_response(no_auth_q)

        invalid_token_q = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Delete constraint reference with invalid credentials", self._pid
        ) as check:
            if invalid_token_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {invalid_token_q.status_code}",
                    query_timestamps=[invalid_token_q.request.timestamp],
                )
        self._gen_val.verify_4xx_response(invalid_token_q)

        if self._test_missing_scope:
            no_scope_q = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Delete constraint reference with missing scope", self._pid
            ) as check:
                if no_scope_q.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {no_scope_q.status_code}",
                        query_timestamps=[no_scope_q.request.timestamp],
                    )
            self._gen_val.verify_4xx_response(no_scope_q)

        if self._test_wrong_scope:
            wrong_scope_q = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Delete constraint reference with incorrect scope", self._pid
            ) as check:
                if wrong_scope_q.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {wrong_scope_q.status_code}",
                        query_timestamps=[wrong_scope_q.request.timestamp],
                    )
            self._gen_val.verify_4xx_response(wrong_scope_q)

        valid_q = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Delete constraint reference with valid credentials", self._pid
        ) as check:
            if valid_q.status_code != 200:
                check.record_failed(
                    summary=f"Expected 200, got {valid_q.status_code}",
                    query_timestamps=[valid_q.request.timestamp],
                )

        with self._scenario.check(
            "Delete constraint reference response format conforms to spec", self._pid
        ) as check:
            try:
                ImplicitDict.parse(
                    valid_q.response.json, ChangeConstraintReferenceResponse
                )
            except ValueError as e:
                check.record_failed(
                    summary="Could not parse the deletion response",
                    details=f"Failed to parse the response body as a ChangeConstraintReferenceResponse: {e}",
                    query_timestamps=[valid_q.request.timestamp],
                )

        self._current_cr = None

    def _verify_cr_search(self):
        op = OPERATIONS[OperationID.QueryConstraintReferences]
        query_kwargs = dict(
            verb=op.verb,
            url=op.path,
            query_type=QueryType.F3548v21DSSQueryConstraintReferences,
            json=QueryConstraintReferenceParameters(
                area_of_interest=self._planning_area_volume4d.to_f3548v21()
            ),
            participant_id=self._dss.participant_id,
        )

        no_auth_q = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Search constraint references with missing credentials",
            self._pid,
        ) as check:
            if no_auth_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {no_auth_q.status_code}",
                    query_timestamps=[no_auth_q.request.timestamp],
                )

        self._gen_val.verify_4xx_response(no_auth_q)

        invalid_token_q = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Search constraint references with invalid credentials",
            self._pid,
        ) as check:
            if invalid_token_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {invalid_token_q.status_code}",
                    query_timestamps=[invalid_token_q.request.timestamp],
                )

        self._gen_val.verify_4xx_response(invalid_token_q)

        if self._test_missing_scope:
            no_scope_q = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Search constraint references with missing scope", self._pid
            ) as check:
                if no_scope_q.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {no_scope_q.status_code}",
                        query_timestamps=[no_scope_q.request.timestamp],
                    )

            self._gen_val.verify_4xx_response(no_scope_q)

        if self._test_wrong_scope:
            wrong_scope_q = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Search constraint references with incorrect scope", self._pid
            ) as check:
                if wrong_scope_q.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {wrong_scope_q.status_code}",
                        query_timestamps=[wrong_scope_q.request.timestamp],
                    )

            self._gen_val.verify_4xx_response(wrong_scope_q)

        valid_q = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Search constraint references with valid credentials", self._pid
        ) as check:
            if valid_q.status_code != 200:
                check.record_failed(
                    summary=f"Expected 200, got {valid_q.status_code}",
                    query_timestamps=[valid_q.request.timestamp],
                )

        with self._scenario.check(
            "Search constraint reference response format conforms to spec",
            self._pid,
        ) as check:
            try:
                ImplicitDict.parse(
                    valid_q.response.json, QueryConstraintReferencesResponse
                )
            except ValueError as e:
                check.record_failed(
                    summary="Could not parse the search response",
                    details=f"Failed to parse the response body as a ChangeConstraintReferenceResponse: {e}",
                    query_timestamps=[valid_q.request.timestamp],
                )

    def _sanity_check_cr_not_created(
        self, check: PendingCheck, creation_q: fetch.Query
    ):
        try:
            _, sanity_check = self._dss.get_constraint_ref(self._test_id)
            self._scenario.record_query(sanity_check)
        except QueryError as qe:
            self._scenario.record_queries(qe.queries)
            if qe.cause_status_code != 404:
                check.record_failed(
                    summary="CR was created by an unauthorized request.",
                    details="The Operational Intent Reference should not have been created, as the creation attempt was not authenticated.",
                    query_timestamps=[
                        creation_q.request.timestamp,
                        qe.cause.request.timestamp,
                    ],
                )
                self._gen_val.verify_4xx_response(qe.cause)

    def _sanity_check_cr_not_updated(
        self, check: PendingCheck, creation_q: fetch.Query
    ):
        try:
            cr, sanity_check = self._dss.get_constraint_ref(self._test_id)
            self._scenario.record_query(sanity_check)
            # Check if the version changed
            if cr.version != self._current_cr.version:
                check.record_failed(
                    summary="CR version updated by an unauthorized request.",
                    details=f"The Constraint Reference with id {self._test_id} should not have been updated, as the update attempt was not authenticated.",
                    query_timestamps=[
                        creation_q.request.timestamp,
                        sanity_check.request.timestamp,
                    ],
                )
            # For the unlikely case where the version would not change but the CR would be mutated anyway:
            if (
                abs(
                    cr.time_end.value.datetime
                    - self._current_cr.time_end.value.datetime
                ).total_seconds()
                > TIME_TOLERANCE_SEC
            ):
                check.record_failed(
                    summary="CR end time updated by an unauthorized request.",
                    details=f"The Constraint Reference with id {self._test_id} should not have been updated, as the update attempt was not authenticated.",
                    query_timestamps=[
                        creation_q.request.timestamp,
                        sanity_check.request.timestamp,
                    ],
                )
        except QueryError as qe:
            self._scenario.record_queries(qe.queries)
            check.record_failed(
                summary="Could not fetch CR to confirm it has not been mutated",
                details=f"The Constraint Reference with id {self._test_id} could not be fetched to confirm it has not been mutated: {qe}",
                query_timestamps=[
                    creation_q.request.timestamp,
                    qe.queries[0].request.timestamp,
                ],
            )
