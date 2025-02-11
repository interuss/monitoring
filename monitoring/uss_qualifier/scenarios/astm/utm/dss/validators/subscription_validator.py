from datetime import datetime
from typing import Optional, List

from uas_standards.astm.f3548.v21.api import SubscriptionID, Subscription

from monitoring.monitorlib import schema_validation
from monitoring.monitorlib.fetch.scd import FetchedSubscription, FetchedSubscriptions
from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.monitorlib.schema_validation import F3548_21
from monitoring.uss_qualifier.resources.astm.f3548.v21.subscription_params import (
    SubscriptionParams,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.validators import (
    fail_with_schema_errors,
)
from monitoring.uss_qualifier.scenarios.scenario import PendingCheck, TestScenario

TIME_TOLERANCE_SEC = 1
"""tolerance when comparing created vs returned timestamps"""


class SubscriptionValidator:
    """
    Wraps the validation logic for a subscription that was returned by the DSS

    It will compare the provided subscription with the parameters specified at its creation.
    """

    _main_check: PendingCheck
    """
    The overarching check corresponding to the general validation of a Subscription.
    This check will be failed if any of the sub-checks carried out by this validator fail.
    """

    _scenario: TestScenario
    """
    Scenario in which this validator is being used. Will be used to register checks.
    """

    _sub_params: Optional[SubscriptionParams]
    _pid: List[str]
    """Participant ID(s) to use for the checks"""

    def __init__(
        self,
        main_check: PendingCheck,
        scenario: TestScenario,
        participant_id: List[str],
        sub_params: Optional[SubscriptionParams],
    ):
        self._main_check = main_check
        self._scenario = scenario
        self._pid = participant_id
        self._sub_params = sub_params

    def _fail_sub_check(
        self, sub_check: PendingCheck, summary: str, details: str, t_dss: datetime
    ) -> None:
        """
        Fail the passed sub check with the passed summary and details, and fail
        the main check with the passed details.

        The provided timestamp is forwarded into the query_timestamps of the check failure.
        """
        sub_check.record_failed(
            summary=summary,
            details=details,
            query_timestamps=[t_dss],
        )

        self._main_check.record_failed(
            summary=f"Invalid subscription returned by the DSS: {summary}",
            details=details,
            query_timestamps=[t_dss],
        )

    def _validate_sub(
        self,
        expected_sub_id: SubscriptionID,
        dss_sub: Subscription,
        t_dss: datetime,
        is_implicit: bool,
        previous_version: Optional[str],
        expected_version: Optional[str],
    ) -> None:
        """
        Args:
            expected_sub_id: the subscription ID we expect to find
            dss_sub: the subscription returned by the DSS
            t_dss: timestamp of the query to the DSS for failure reporting
            is_implicit: whether the subscription was implicitly created or not
            previous_version: previous version of the subscription, if we are verifying a mutated subscription
            expected_version: expected version of the subscription, if we are verifying a queried subscription
        """

        with self._scenario.check(
            "Returned subscription ID is correct", self._pid
        ) as check:
            if dss_sub.id != expected_sub_id:
                self._fail_sub_check(
                    check,
                    summary=f"Returned subscription ID is incorrect",
                    details=f"Expected subscription ID {expected_sub_id} but got {dss_sub.id}",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Returned subscription has an USS base URL", self._pid
        ) as check:
            # If uss_base_url is not present, or it is None or Empty, we should fail:
            if "uss_base_url" not in dss_sub or not dss_sub.uss_base_url:
                self._fail_sub_check(
                    check,
                    summary="Returned subscription has no USS base URL",
                    details="The subscription returned by the DSS has no USS base URL when it should have one",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Returned USS base URL has correct base URL", self._pid
        ) as check:
            if dss_sub.uss_base_url != self._sub_params.base_url:
                self._fail_sub_check(
                    check,
                    summary="Returned USS Base URL does not match provided one",
                    details=f"Provided: {self._sub_params.base_url}, Returned: {dss_sub.uss_base_url}",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Returned subscription has a start time", self._pid
        ) as check:
            if "time_start" not in dss_sub or dss_sub.time_start is None:
                self._fail_sub_check(
                    check,
                    summary="Returned subscription has no start time",
                    details="The subscription returned by the DSS has no start time when it should have one",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Returned subscription has an end time", self._pid
        ) as check:
            if "time_end" not in dss_sub or dss_sub.time_end is None:
                self._fail_sub_check(
                    check,
                    summary="Returned subscription has no end time",
                    details="The subscription returned by the DSS has no end time when it should have one",
                    t_dss=t_dss,
                )

        # When expect_start_time and expect_end_time have not been defined, there is no clear specification on
        # what the returned times should be, so we only check them when we have requested them.
        if self._sub_params.start_time is not None:
            with self._scenario.check(
                "Returned start time is correct", self._pid
            ) as check:
                if (
                    abs(
                        dss_sub.time_start.value.datetime - self._sub_params.start_time
                    ).total_seconds()
                    > TIME_TOLERANCE_SEC
                ):
                    self._fail_sub_check(
                        check,
                        summary="Returned start time does not match provided one",
                        details=f"Provided: {self._sub_params.start_time}, Returned: {dss_sub.time_start}",
                        t_dss=t_dss,
                    )

        if self._sub_params.end_time is not None:
            with self._scenario.check(
                "Returned end time is correct", self._pid
            ) as check:
                if (
                    abs(
                        dss_sub.time_end.value.datetime - self._sub_params.end_time
                    ).total_seconds()
                    > TIME_TOLERANCE_SEC
                ):
                    self._fail_sub_check(
                        check,
                        summary="Returned end time does not match provided one",
                        details=f"Provided: {self._sub_params.end_time}, Returned: {dss_sub.time_end}",
                        t_dss=t_dss,
                    )

        with self._scenario.check(
            "Returned subscription has a version", self._pid
        ) as check:
            if not dss_sub.version:
                self._fail_sub_check(
                    check,
                    summary="Returned subscription has no version",
                    details="A subscription is expected to have a version",
                    t_dss=t_dss,
                )

        # If the previous version is not None, we are dealing with a mutation:
        if previous_version is not None:
            with self._scenario.check(
                "Mutated subscription version is updated", self._pid
            ) as check:
                if dss_sub.version == previous_version:
                    self._fail_sub_check(
                        check,
                        summary="Returned subscription version was not updated",
                        details=f"Expected version to be different from {previous_version}, but it was not",
                        t_dss=t_dss,
                    )

        if expected_version is not None:
            with self._scenario.check(
                "Non-mutated subscription keeps the same version", self._pid
            ) as check:
                if dss_sub.version != expected_version:
                    self._fail_sub_check(
                        check,
                        summary="Returned subscription version was updated",
                        details=f"Expected version to be {expected_version}, Returned: {dss_sub.version}",
                        t_dss=t_dss,
                    )

        if is_implicit:
            with self._scenario.check(
                "Implicit subscription has implicit flag set to true", self._pid
            ) as check:
                if not dss_sub.implicit_subscription:
                    self._fail_sub_check(
                        check,
                        summary="Returned subscription has implicit flag set to false",
                        details="Expected the subscription to be implicit, but it was not",
                        t_dss=t_dss,
                    )
        else:
            with self._scenario.check(
                "Non-implicit subscription has implicit flag set to false", self._pid
            ) as check:
                if dss_sub.implicit_subscription:
                    self._fail_sub_check(
                        check,
                        summary="Returned subscription has implicit flag set to true",
                        details="Expected the subscription to not be implicit, but it was",
                        t_dss=t_dss,
                    )

        with self._scenario.check(
            "Operational intents notification flag is as requested", self._pid
        ) as check:
            if (
                dss_sub.notify_for_operational_intents
                != self._sub_params.notify_for_op_intents
            ):
                self._fail_sub_check(
                    check,
                    summary="Operational intents notification flag is not as requested",
                    details=f"Provided: {self._sub_params.notify_for_op_intents}, Returned: {dss_sub.notify_for_operational_intents}",
                    t_dss=t_dss,
                )

        with self._scenario.check(
            "Constraints notification flag is as requested", self._pid
        ) as checK:
            if (
                dss_sub.notify_for_constraints
                != self._sub_params.notify_for_constraints
            ):
                self._fail_sub_check(
                    check,
                    summary="Constraints notification flag is not as requested",
                    details=f"Provided: {self._sub_params.notify_for_constraints}, Returned: {dss_sub.notify_for_constraints}",
                    t_dss=t_dss,
                )

    def _validate_put_sub_response_schema(
        self, new_sub: MutatedSubscription, t_dss: datetime, action: str
    ):
        """Validate response bodies for creation and mutation of subscriptions."""

        check_name = (
            "Create subscription response format conforms to spec"
            if action == "create"
            else "Mutate subscription response format conforms to spec"
        )

        with self._scenario.check(check_name, self._pid) as check:
            errors = schema_validation.validate(
                F3548_21.OpenAPIPath,
                F3548_21.PutSubscriptionResponse,
                new_sub.response.json,
            )
            if errors:
                fail_with_schema_errors(check, errors, t_dss)

    def validate_created_subscription(
        self, expected_sub_id: SubscriptionID, new_sub: MutatedSubscription
    ) -> None:
        """Validate a subscription that was just explicitly created, meaning
        we don't have a previous version to compare to, and we expect it to not be an implicit one.
        """
        (t_dss, sub) = (new_sub.request.timestamp, new_sub.subscription)

        # Validate the response schema
        self._validate_put_sub_response_schema(new_sub, t_dss, "create")

        # Validate the subscription itself
        self._validate_sub(
            expected_sub_id=expected_sub_id,
            dss_sub=new_sub.subscription,
            t_dss=t_dss,
            is_implicit=False,
            previous_version=None,
            expected_version=None,
        )

        # Check that the notification index is 0 for a newly created subscription.
        # Should the notification field be missing, we assume it will have defaulted to 0 on the DSS's side.
        with self._scenario.check(
            "New subscription has a notification index of 0", self._pid
        ) as check:
            notif_index = new_sub.subscription.notification_index
            if notif_index != 0:
                self._fail_sub_check(
                    check,
                    summary=f"Returned notification index was {notif_index} instead of 0",
                    details="A subscription is expected to have a notification index of 0 when it is created"
                    f"Parameters used: {self._sub_params}",
                    t_dss=t_dss,
                )

    def _check_notif_index_equal_or_above_0(
        self, notif_index: int, t_dss: datetime
    ) -> None:
        """Check the notification index is 0 or more, if it is present.
        (notifications might have been sent out between the creation and subsequent query)
        Should the index be absent, we assume it to be 0 on the DSS's side.
        """
        with self._scenario.check(
            "Returned notification index is equal to or greater than 0", self._pid
        ) as check:
            if notif_index < 0:
                self._fail_sub_check(
                    check,
                    summary="Returned notification index is lower than 0",
                    details=f"Returned: {notif_index} when 0 or more was expected. Parameters used: {self._sub_params}",
                    t_dss=t_dss,
                )

    def validate_mutated_subscription(
        self,
        expected_sub_id: SubscriptionID,
        mutated_sub: MutatedSubscription,
        previous_version: str,
        is_implicit: bool,
    ) -> None:
        """Validate a subscription that was just mutated, meaning we have a previous version to compare to.
        Callers must specify if this is an implicit subscription or not."""
        (t_dss, sub) = (mutated_sub.request.timestamp, mutated_sub.subscription)

        # Validate the response schema
        self._validate_put_sub_response_schema(mutated_sub, t_dss, "mutate")

        # Validate the subscription itself
        self._validate_sub(
            expected_sub_id=expected_sub_id,
            dss_sub=mutated_sub.subscription,
            t_dss=t_dss,
            is_implicit=is_implicit,
            previous_version=previous_version,
            expected_version=None,
        )

        self._check_notif_index_equal_or_above_0(sub.notification_index, t_dss)

    def validate_fetched_subscription(
        self,
        expected_sub_id: SubscriptionID,
        fetched_sub: FetchedSubscription,
        expected_version: str,
        is_implicit: bool,
    ) -> None:
        """Validate a subscription that was directly queried by its ID.
        Callers must specify if this is an implicit subscription or not."""

        (t_dss, sub) = (fetched_sub.request.timestamp, fetched_sub.subscription)

        # Validate the response schema
        with self._scenario.check(
            "Get subscription response format conforms to spec", self._pid
        ) as check:
            errors = schema_validation.validate(
                F3548_21.OpenAPIPath,
                F3548_21.GetSubscriptionResponse,
                fetched_sub.response.json,
            )
            if errors:
                fail_with_schema_errors(check, errors, t_dss)

        # Validate the subscription itself
        self._validate_sub(
            expected_sub_id=expected_sub_id,
            dss_sub=fetched_sub.subscription,
            t_dss=t_dss,
            is_implicit=is_implicit,
            previous_version=None,
            expected_version=expected_version,
        )

        self._check_notif_index_equal_or_above_0(sub.notification_index, t_dss)

    def validate_searched_subscription(
        self,
        expected_sub_id: SubscriptionID,
        searched_subscriptions: FetchedSubscriptions,
        expected_version: str,
        is_implicit: bool,
    ) -> None:
        """Validate a subscription that was retrieved through search.
        Note that the callers need to pass the entire response from the DSS, as the schema check
        will be performed on the entire response, not just the subscription itself.
        However, only the expected subscription is checked for the correctness of its contents.
        """

        (t_dss, subs) = (
            searched_subscriptions.request.timestamp,
            searched_subscriptions.subscriptions,
        )

        # Validate the response schema
        self.validate_searched_subscriptions_format(searched_subscriptions, t_dss)

        with self._scenario.check(
            "Created Subscription is in search results", self._pid
        ) as check:
            if expected_sub_id not in subs:
                self._fail_sub_check(
                    check,
                    summary="Created subscription is not present in search results",
                    details=f"The subscription {expected_sub_id} was expected to be found in the search results, but these only contained the following subscriptions: {subs.keys()}",
                    t_dss=t_dss,
                )
                # Depending on the severity defined in the documentation, the above might not raise an exception,
                # and we should still stop here if the check failed.
                return

        sub = subs[expected_sub_id]

        # Validate the subscription itself
        self._validate_sub(
            expected_sub_id=expected_sub_id,
            dss_sub=sub,
            t_dss=t_dss,
            is_implicit=is_implicit,
            previous_version=None,
            expected_version=expected_version,
        )

        self._check_notif_index_equal_or_above_0(sub.notification_index, t_dss)

    def validate_searched_subscriptions_format(
        self, searched_subscriptions: FetchedSubscriptions, t_dss: datetime
    ) -> None:
        # Validate the response schema
        with self._scenario.check(
            "Search subscriptions response format conforms to spec", self._pid
        ) as check:
            errors = schema_validation.validate(
                F3548_21.OpenAPIPath,
                F3548_21.QuerySubscriptionsResponse,
                searched_subscriptions.response.json,
            )
            if errors:
                fail_with_schema_errors(check, errors, t_dss)

    def validate_deleted_subscription(
        self,
        expected_sub_id: SubscriptionID,
        deleted_subscription: MutatedSubscription,
        expected_version: str,
        is_implicit: bool,
    ) -> None:
        """Validate a subscription that was just deleted.
        Callers must specify if this is an implicit subscription or not."""

        (t_dss, sub) = (
            deleted_subscription.request.timestamp,
            deleted_subscription.subscription,
        )

        # Validate the response schema
        with self._scenario.check(
            "Delete subscription response format conforms to spec", self._pid
        ) as check:
            errors = schema_validation.validate(
                F3548_21.OpenAPIPath,
                F3548_21.DeleteSubscriptionResponse,
                deleted_subscription.response.json,
            )
            if errors:
                fail_with_schema_errors(check, errors, t_dss)

        # Validate the subscription itself
        self._validate_sub(
            expected_sub_id=expected_sub_id,
            dss_sub=sub,
            t_dss=t_dss,
            is_implicit=is_implicit,
            previous_version=None,
            expected_version=expected_version,
        )

        self._check_notif_index_equal_or_above_0(sub.notification_index, t_dss)
