import datetime
from typing import Dict

from monitoring.monitorlib.mutate.rid import ChangedSubscription
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import (
    GenericTestScenario,
    PendingCheck,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext

_24H_MIN_TOLERANCE_S = 23 * 3600 + 59 * 60  # 23 hours and 59 minutes
_24H_MAX_TOLERANCE_S = 24 * 3600 + 1  # 24 hours sharp, plus a second


class SubscriptionValidation(GenericTestScenario):
    """Based on prober/rid/v2/test_subscription_validation.py from the legacy prober tool."""

    SUB_TYPE = register_resource_type(367, "Subscription")

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        isa: ServiceAreaResource,
    ):
        """

        Args:
            dss: dss to test
            id_generator: will let us generate specific identifiers
            isa: Service Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.
        """
        super().__init__()
        # This is an UTMClientSession
        self._dss = dss.dss_instance
        self._dss_wrapper = DSSWrapper(self, self._dss)
        # TODO: the id_factory seems to generate static IDs:
        #  for creating different subscriptions this probably won't do.
        self._sub_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._isa = isa.specification
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self._setup_case()

        self.begin_test_case("Subscription duration limitations")
        self._create_too_long_subscription()
        self.end_test_case()

        self.begin_test_case("Subscription quantity limitations")
        self._create_too_many_subscriptions()
        self.end_test_case()

        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")

        self._ensure_clean_workspace_step()

        self.end_test_case()

    def _clean_any_sub(self):
        self._dss_wrapper.cleanup_subs_in_area(self._isa_area)

    def _ensure_clean_workspace_step(self):
        self.begin_test_step("Ensure clean workspace")

        self._clean_any_sub()

        self.end_test_step()

    def _create_too_many_subscriptions(self):
        self.begin_test_step("Create maximum number of subscriptions")

        with self.check(
            "Create up to the maximum allowed number of subscriptions in an area",
            [self._dss.participant_id],
        ) as check:
            # Create 10 subscriptions with different ID's
            for i in range(self._dss.rid_version.dss_max_subscriptions_per_area):
                sub_id = f"{self._sub_id[:-3]}1{i:02d}"
                self._dss_wrapper.put_sub(
                    check,
                    sub_id=sub_id,
                    **self._default_subscription_params(datetime.timedelta(minutes=30)),
                )

        self.end_test_step()

        self.begin_test_step("Exceed maximum number of subscriptions")

        with self.check(
            "Enforce maximum number of subscriptions for an area",
            [self._dss.participant_id],
        ) as check:
            self._dss_wrapper.put_sub_expect_response_code(
                check=check,
                sub_id=f"{self._sub_id[:-3]}200",
                expected_error_codes={
                    400,  # Expecting a 429 but a 400 is acceptable too
                    429,
                },
                **self._default_subscription_params(datetime.timedelta(minutes=30)),
            )

        self.end_test_step()

        self.begin_test_step("Clean up subscriptions")

        self._clean_any_sub()

        self.end_test_step()

    def _create_too_long_subscription(self):
        self.begin_test_step("Try to create too-long subscription")

        with self.check(
            "Too-long subscription creation rejected",
            [self._dss.participant_id],
        ) as check:
            # Sub with this ID does not exist and too long: we expect either a failure, or
            # that any subscription that is effectively created to be truncated at 24 hours.
            creation_attempt = self._dss_wrapper.put_sub_expect_response_code(
                check=check,
                sub_id=self._sub_id,
                expected_error_codes={
                    200,
                    400,
                },  # success is tolerated if the subscription is properly truncated
                **self._default_subscription_params(
                    datetime.timedelta(hours=24, minutes=10)
                ),
            )

            if creation_attempt.success:
                self._check_properly_truncated(check, creation_attempt)

        self.end_test_step()

        self.begin_test_step("Try to extend subscription")

        with self.check(
            "Valid subscription created",
            [self._dss.participant_id],
        ) as check:
            # Create a subscription that is fine
            sub = self._dss_wrapper.put_sub(
                check=check,
                sub_id=self._sub_id,
                **self._default_subscription_params(
                    datetime.timedelta(hours=23, minutes=59)
                ),
            )

        with self.check(
            "Subscription duration limited during update",
            [self._dss.participant_id],
        ) as check:
            # Sub with this ID does exist, and we try to extend it beyond 24 hours:
            extended_subscription = self._dss_wrapper.put_sub_expect_response_code(
                check=check,
                sub_id=self._sub_id,
                expected_error_codes={200, 400},
                **self._default_subscription_params(
                    datetime.timedelta(hours=24, minutes=10)
                ),
            )
            if extended_subscription.success:
                self._check_properly_truncated(check, extended_subscription)

        self.end_test_step()

        self.begin_test_step("Remove subscription")

        with self.check(
            "Subscription deleted",
            [self._dss.participant_id],
        ) as check:
            self._dss_wrapper.del_sub(
                check=check, sub_id=self._sub_id, sub_version=sub.subscription.version
            )

        self.end_test_step()

    def _check_properly_truncated(
        self, check: PendingCheck, changed: ChangedSubscription
    ):
        duration = changed.subscription.duration
        # In case of success, we obtained the effectively created subscription:
        if _24H_MIN_TOLERANCE_S < duration.total_seconds() < _24H_MAX_TOLERANCE_S:
            # All is good
            pass
        else:
            check.record_failed(
                "Created record subscription has not been properly truncated to 24 hours",
                Severity.Medium,
                f"{self._dss.participant_id} DSS instance has returned a non-properly truncated subscription "
                f"(duration: {duration}) "
                f"when the expectation was either to fail or to truncate at 24 hours.",
                query_timestamps=[changed.query.request.timestamp],
            )
            # If a subscription was created, we want to delete it before continuing:
            self._dss_wrapper.cleanup_sub(sub_id=self._sub_id)

    def _default_subscription_params(self, duration: datetime.timedelta) -> Dict:
        now = datetime.datetime.utcnow()
        return dict(
            area_vertices=[vertex.as_s2sphere() for vertex in self._isa.footprint],
            alt_lo=self._isa.altitude_min,
            alt_hi=self._isa.altitude_max,
            start_time=now,
            end_time=now + duration,
            uss_base_url=self._isa.base_url,
        )

    def cleanup(self):
        self.begin_cleanup()

        self._clean_any_sub()

        self.end_cleanup()
