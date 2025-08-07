from datetime import datetime, timedelta
from typing import Optional

from uas_standards.astm.f3548.v21.api import (
    OPERATIONS,
    OperationID,
    QuerySubscriptionParameters,
)

from monitoring.monitorlib import fetch
from monitoring.monitorlib.fetch import QueryType
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.mutate import scd as mutate
from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.planning_area import PlanningAreaSpecification
from monitoring.uss_qualifier.scenarios.astm.utm.dss.authentication.generic import (
    GenericAuthValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import PendingCheck, TestScenario

TIME_TOLERANCE_SEC = 1


class SubscriptionAuthValidator:
    def __init__(
        self,
        scenario: TestScenario,
        generic_validator: GenericAuthValidator,
        dss: DSSInstance,
        test_id: str,
        planning_area: PlanningAreaSpecification,
        planning_area_volume4d: Volume4D,
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
        self._planning_area_volume4d = planning_area_volume4d

        self._sub_params = self._planning_area.get_new_subscription_params(
            subscription_id=self._test_id,
            # Set this slightly in the past: we will update the subscriptions
            # to a later value that still needs to be roughly 'now' without getting into the future
            start_time=datetime.now().astimezone() - timedelta(seconds=10),
            duration=timedelta(minutes=45),
            # This is a planning area without constraint processing
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )

        self._no_auth_session = no_auth_session
        self._invalid_token_session = invalid_token_session

        self._test_wrong_scope = test_wrong_scope
        self._test_missing_scope = test_missing_scope

    def verify_sub_endpoints_authentication(self):
        self._verify_sub_creation()
        self._verify_sub_get()
        self._verify_sub_mutation()
        self._verify_sub_deletion()
        self._verify_sub_search()

    def _verify_sub_creation(self):
        # Subscription creation request:
        sub_params = dict(**self._sub_params)
        op = OPERATIONS[OperationID.CreateSubscription]
        del sub_params["sub_id"]
        query_kwargs = dict(
            verb=op.verb,
            url=op.path.format(subscriptionid=self._sub_params.sub_id),
            json=mutate.build_upsert_subscription_params(**sub_params),
            query_type=QueryType.F3548v21DSSCreateSubscription,
            participant_id=self._dss.participant_id,
        )

        # No auth:
        no_auth_q = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Create subscription with missing credentials", self._pid
        ) as check:
            if no_auth_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {no_auth_q.status_code}",
                    query_timestamps=[no_auth_q.request.timestamp],
                )

            self._sanity_check_sub_not_created(check, no_auth_q)

        self._gen_val.verify_4xx_response(no_auth_q)

        # Bad token signature:
        invalid_token_q = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Create subscription with invalid credentials", self._pid
        ) as check:
            if invalid_token_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {invalid_token_q.status_code}",
                    query_timestamps=[invalid_token_q.request.timestamp],
                )

            self._sanity_check_sub_not_created(check, invalid_token_q)

        self._gen_val.verify_4xx_response(invalid_token_q)

        # Valid credentials but missing scope:
        if self._test_missing_scope:
            no_scope_q = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Create subscription with missing scope", self._pid
            ) as check:
                if no_scope_q.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {no_scope_q.status_code}",
                        query_timestamps=[no_scope_q.request.timestamp],
                    )

                self._sanity_check_sub_not_created(check, no_scope_q)
            self._gen_val.verify_4xx_response(no_scope_q)

        # Valid credentials but wrong scope:
        if self._test_wrong_scope:
            wrong_scope_q = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Create subscription with incorrect scope", self._pid
            ) as check:
                if wrong_scope_q.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {wrong_scope_q.status_code}",
                        details="With an incorrect scope, the DSS should return a 403 without any data.",
                        query_timestamps=[wrong_scope_q.request.timestamp],
                    )

                self._sanity_check_sub_not_created(check, wrong_scope_q)
            self._gen_val.verify_4xx_response(wrong_scope_q)

        # Correct token:
        #  - confirms that the request would otherwise work
        #  - makes a subscription available for read/mutation tests
        create_ok_q = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Create subscription with valid credentials", self._pid
        ) as check:
            if create_ok_q.status_code != 200:
                check.record_failed(
                    summary=f"Expected 200, got {create_ok_q.status_code}",
                    query_timestamps=[create_ok_q.request.timestamp],
                )

        # Store the subscription
        self._current_sub = MutatedSubscription(create_ok_q).subscription

    def _verify_sub_get(self):
        op = OPERATIONS[OperationID.GetSubscription]

        query_kwargs = dict(
            verb=op.verb,
            url=op.path.format(subscriptionid=self._sub_params.sub_id),
            query_type=QueryType.F3548v21DSSGetSubscription,
            participant_id=self._dss.participant_id,
        )

        query_no_auth = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Get subscription with missing credentials", self._pid
        ) as check:
            if query_no_auth.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {query_no_auth.status_code}",
                    query_timestamps=[query_no_auth.request.timestamp],
                )

        self._gen_val.verify_4xx_response(query_no_auth)

        query_invalid_token = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Get subscription with invalid credentials", self._pid
        ) as check:
            if query_invalid_token.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {query_invalid_token.status_code}",
                    query_timestamps=[query_invalid_token.request.timestamp],
                )

        self._gen_val.verify_4xx_response(query_invalid_token)

        if self._test_missing_scope:
            query_missing_scope = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Get subscription with missing scope", self._pid
            ) as check:
                if query_missing_scope.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {query_missing_scope.status_code}",
                        details="Without the proper scope, the DSS should return a 401 without any data.",
                        query_timestamps=[query_missing_scope.request.timestamp],
                    )

            self._gen_val.verify_4xx_response(query_missing_scope)

        if self._test_wrong_scope:
            query_wrong_scope = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Get subscription with incorrect scope", self._pid
            ) as check:
                if query_wrong_scope.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {query_wrong_scope.status_code}",
                        details="With an incorrect scope, the DSS should return a 403 without any data.",
                        query_timestamps=[query_wrong_scope.request.timestamp],
                    )

            self._gen_val.verify_4xx_response(query_wrong_scope)

        query_ok = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Get subscription with valid credentials", self._pid
        ) as check:
            if query_ok.status_code != 200:
                check.record_failed(
                    summary=f"Expected 200, got {query_ok.status_code}",
                    query_timestamps=[query_ok.request.timestamp],
                )

    def _verify_sub_mutation(self):
        # Subscription creation request:
        new_params = self._sub_params.copy()
        new_params.end_time = new_params.end_time - timedelta(seconds=10)
        pld_params = dict(**new_params)
        op = OPERATIONS[OperationID.UpdateSubscription]
        del pld_params["sub_id"]

        query_kwargs = dict(
            verb=op.verb,
            url=op.path.format(
                subscriptionid=self._sub_params.sub_id,
                version=self._current_sub.version,
            ),
            json=mutate.build_upsert_subscription_params(**pld_params),
            query_type=QueryType.F3548v21DSSCreateSubscription,
            participant_id=self._dss.participant_id,
        )

        no_auth_q = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Mutate subscription with missing credentials", self._pid
        ) as check:
            if no_auth_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {no_auth_q.status_code}",
                    query_timestamps=[no_auth_q.request.timestamp],
                )
            # Sanity check: confirm the subscription was not mutated by the faulty call:
            self._sanity_check_sub_not_mutated(check, no_auth_q)

        self._gen_val.verify_4xx_response(no_auth_q)

        invalid_token_q = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Mutate subscription with invalid credentials", self._pid
        ) as check:
            if invalid_token_q.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {invalid_token_q.status_code}",
                    query_timestamps=[invalid_token_q.request.timestamp],
                )
            # Sanity check: confirm the subscription was not mutated by the faulty call:
            self._sanity_check_sub_not_mutated(check, invalid_token_q)

        self._gen_val.verify_4xx_response(invalid_token_q)

        if self._test_missing_scope:
            query_missing_scope = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Mutate subscription with missing scope", self._pid
            ) as check:
                if query_missing_scope.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {query_missing_scope.status_code}",
                        details="Without the proper scope, the DSS should return a 401 without any data.",
                        query_timestamps=[query_missing_scope.request.timestamp],
                    )
                # Sanity check: confirm the subscription was not mutated by the faulty call:
                self._sanity_check_sub_not_mutated(check, query_missing_scope)

            self._gen_val.verify_4xx_response(query_missing_scope)

        if self._test_wrong_scope:
            query_wrong_scope = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Mutate subscription with incorrect scope", self._pid
            ) as check:
                if query_wrong_scope.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {query_wrong_scope.status_code}",
                        details="With an incorrect scope, the DSS should return a 403 without any data.",
                        query_timestamps=[query_wrong_scope.request.timestamp],
                    )
                # Sanity check: confirm the subscription was not mutated by the faulty call:
                self._sanity_check_sub_not_mutated(check, query_wrong_scope)
            self._gen_val.verify_4xx_response(query_wrong_scope)

        mutate_ok_q = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Mutate subscription with valid credentials", self._pid
        ) as check:
            if mutate_ok_q.status_code != 200:
                check.record_failed(
                    summary=f"Expected 200, got {mutate_ok_q.status_code}",
                    query_timestamps=[mutate_ok_q.request.timestamp],
                )

        self._current_sub = MutatedSubscription(mutate_ok_q).subscription

    def _verify_sub_deletion(self):
        op = OPERATIONS[OperationID.DeleteSubscription]

        query_kwargs = dict(
            verb=op.verb,
            url=op.path.format(
                subscriptionid=self._sub_params.sub_id,
                version=self._current_sub.version,
            ),
            query_type=QueryType.F3548v21DSSDeleteSubscription,
            participant_id=self._dss.participant_id,
        )

        query_no_auth = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Delete subscription with missing credentials", self._pid
        ) as check:
            if query_no_auth.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {query_no_auth.status_code}",
                    query_timestamps=[query_no_auth.request.timestamp],
                )
            # Sanity check
            self._sanity_check_sub_not_deleted(check, query_no_auth)

        self._gen_val.verify_4xx_response(query_no_auth)

        query_invalid_token = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Delete subscription with invalid credentials", self._pid
        ) as check:
            if query_invalid_token.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {query_invalid_token.status_code}",
                    query_timestamps=[query_invalid_token.request.timestamp],
                )
            # Sanity check
            self._sanity_check_sub_not_deleted(check, query_invalid_token)

        self._gen_val.verify_4xx_response(query_invalid_token)

        if self._test_missing_scope:
            query_missing_scope = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Delete subscription with missing scope", self._pid
            ) as check:
                if query_missing_scope.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {query_missing_scope.status_code}",
                        details="Without the proper scope, the DSS should return a 401 without any data.",
                        query_timestamps=[query_missing_scope.request.timestamp],
                    )
                # Sanity check
                self._sanity_check_sub_not_deleted(check, query_missing_scope)

            self._gen_val.verify_4xx_response(query_missing_scope)

        if self._test_wrong_scope:
            query_wrong_scope = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Delete subscription with incorrect scope", self._pid
            ) as check:
                if query_wrong_scope.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {query_wrong_scope.status_code}",
                        details="With an incorrect scope, the DSS should return a 403 without any data.",
                        query_timestamps=[query_wrong_scope.request.timestamp],
                    )
                # Sanity check
                self._sanity_check_sub_not_deleted(check, query_wrong_scope)

            self._gen_val.verify_4xx_response(query_wrong_scope)

        query_ok = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Delete subscription with valid credentials", self._pid
        ) as check:
            if query_ok.status_code != 200:
                check.record_failed(
                    summary=f"Expected 200, got {query_ok.status_code}",
                    query_timestamps=[query_ok.request.timestamp],
                )

        # Confirm the subscription was deleted
        not_found = self._dss.get_subscription(self._sub_params.sub_id)
        with self._scenario.check(
            "Delete subscription with valid credentials", self._pid
        ) as check:
            if not_found.status_code != 404:
                check.record_failed(
                    summary=f"Expected 404, got {not_found.status_code}",
                    details="The subscription should have been deleted, as the deletion attempt was appropriately authenticated.",
                    query_timestamps=[
                        query_ok.request.timestamp,
                        not_found.request.timestamp,
                    ],
                )

    def _verify_sub_search(self):
        op = OPERATIONS[OperationID.QuerySubscriptions]

        query_kwargs = dict(
            verb=op.verb,
            url=op.path,
            query_type=QueryType.F3548v21DSSQuerySubscriptions,
            json=QuerySubscriptionParameters(
                area_of_interest=self._planning_area_volume4d
            ),
            participant_id=self._dss.participant_id,
        )

        query_no_auth = self._gen_val.query_no_auth(**query_kwargs)
        with self._scenario.check(
            "Search subscriptions with missing credentials", self._pid
        ) as check:
            if query_no_auth.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {query_no_auth.status_code}",
                    details="Without valid credentials, the DSS should return a 401 without any data.",
                    query_timestamps=[query_no_auth.request.timestamp],
                )

        self._gen_val.verify_4xx_response(query_no_auth)

        query_invalid_token = self._gen_val.query_invalid_token(**query_kwargs)
        with self._scenario.check(
            "Search subscriptions with invalid credentials", self._pid
        ) as check:
            if query_invalid_token.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {query_invalid_token.status_code}",
                    details="Without valid credentials, the DSS should return a 401 without any data.",
                    query_timestamps=[query_invalid_token.request.timestamp],
                )

        self._gen_val.verify_4xx_response(query_invalid_token)

        if self._test_missing_scope:
            query_missing_scope = self._gen_val.query_missing_scope(**query_kwargs)
            with self._scenario.check(
                "Search subscriptions with missing scope", self._pid
            ) as check:
                if query_missing_scope.status_code != 401:
                    check.record_failed(
                        summary=f"Expected 401, got {query_missing_scope.status_code}",
                        details="Without the proper scope, the DSS should return a 401 without any data.",
                        query_timestamps=[query_missing_scope.request.timestamp],
                    )

            self._gen_val.verify_4xx_response(query_missing_scope)

        if self._test_wrong_scope:
            query_wrong_scope = self._gen_val.query_wrong_scope(
                scope=self._test_wrong_scope, **query_kwargs
            )
            with self._scenario.check(
                "Search subscriptions with incorrect scope", self._pid
            ) as check:
                if query_wrong_scope.status_code != 403:
                    check.record_failed(
                        summary=f"Expected 403, got {query_wrong_scope.status_code}",
                        details="With an incorrect scope, the DSS should return a 403 without any data.",
                        query_timestamps=[query_wrong_scope.request.timestamp],
                    )

            self._gen_val.verify_4xx_response(query_wrong_scope)

        query_ok = self._gen_val.query_valid_auth(**query_kwargs)
        with self._scenario.check(
            "Search subscriptions with valid credentials", self._pid
        ) as check:
            if query_ok.status_code != 200:
                check.record_failed(
                    summary=f"Expected 200, got {query_ok.status_code}",
                    query_timestamps=[query_ok.request.timestamp],
                )

    def _sanity_check_sub_not_created(
        self, check: PendingCheck, creation_q: fetch.Query
    ):
        sanity_check = self._dss.get_subscription(self._sub_params.sub_id)
        self._scenario.record_query(sanity_check)
        if sanity_check.status_code != 404:
            check.record_failed(
                summary="Subscription was created by an unauthorized request.",
                details="The subscription should not have been created, as the creation attempt was not authenticated.",
                query_timestamps=[
                    creation_q.request.timestamp,
                    sanity_check.request.timestamp,
                ],
            )
        self._gen_val.verify_4xx_response(sanity_check)

    def _sanity_check_sub_not_mutated(
        self, check: PendingCheck, mutation_q: fetch.Query
    ):
        sanity_check = self._dss.get_subscription(self._sub_params.sub_id)
        self._scenario.record_query(sanity_check)
        if (
            abs(
                sanity_check.subscription.time_end.value.datetime
                - self._current_sub.time_end.value.datetime
            ).total_seconds()
            > TIME_TOLERANCE_SEC
        ):
            check.record_failed(
                summary="Subscription was mutated by an unauthorized query.",
                details="The subscription should not have been mutated, as the mutation attempt was not appropriately authenticated.",
                query_timestamps=[
                    mutation_q.request.timestamp,
                    sanity_check.request.timestamp,
                ],
            )

    def _sanity_check_sub_not_deleted(
        self, check: PendingCheck, deletion_q: fetch.Query
    ):
        sanity_check = self._dss.get_subscription(self._sub_params.sub_id)
        self._scenario.record_query(sanity_check)
        if sanity_check.status_code == 404:
            check.record_failed(
                summary="Unauthorized request could delete the subscription.",
                details="The subscription should not have been deleted, as the deletion attempt was not authenticated.",
                query_timestamps=[
                    deletion_q.request.timestamp,
                    sanity_check.request.timestamp,
                ],
            )
        elif sanity_check.status_code != 200:
            check.record_failed(
                summary=f"Expected 200, got {sanity_check.status_code}",
                details="The subscription should not have been deleted, as the deletion attempt was not appropriately authenticated.",
                query_timestamps=[
                    deletion_q.request.timestamp,
                    sanity_check.request.timestamp,
                ],
            )
