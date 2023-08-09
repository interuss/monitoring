from datetime import timedelta

import arrow
import datetime

from monitoring.monitorlib import schema_validation
from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.rid import RIDVersion
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
from monitoring.monitorlib.mutate.rid import ChangedSubscription

from typing import Dict


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

    def run(self):
        self.begin_test_scenario()

        self._setup_case()
        self._subscription_limitations_case()

        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")

        self._ensure_clean_workspace_step()

        self.end_test_case()

    def _clean_any_sub(self):
        with self.check(
            "Successful subscription query and cleanup", [self._dss.participant_id]
        ) as check:
            fetched = self._dss_wrapper.search_subs(
                check, self._isa.footprint.to_vertices()
            )

            for sub_id in fetched.subscriptions.keys():
                self._dss_wrapper.cleanup_sub(check, sub_id=sub_id)

    def _ensure_clean_workspace_step(self):
        self.begin_test_step("Ensure clean workspace")

        self._clean_any_sub()

        self.end_test_step()

    def _subscription_limitations_case(self):
        self.begin_test_case("Subscription limitations")
        self.begin_test_step("Subscription limitations")

        self._create_too_long_subscription()

        self.end_test_step()
        self.end_test_case()

    def _create_too_long_subscription(self):
        with self.check(
            "Enforce maximum duration of subscriptions for an area",
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

            # Create a subscription that is fine
            self._dss_wrapper.put_sub(
                check=check,
                sub_id=self._sub_id,
                **self._default_subscription_params(
                    datetime.timedelta(hours=23, minutes=59)
                ),
            )

            # Sub with this ID does exist, an we try to extend it beyond 24 hours:
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
                f"when the expecation was either to fail or to truncate at 24 hours.",
                query_timestamps=[changed.query.request.timestamp],
            )
            # If a subscription was created, we want to delete it before continuing:
            self._dss_wrapper.cleanup_sub(check, sub_id=self._sub_id)

    def _default_subscription_params(self, duration: datetime.timedelta) -> Dict:
        now = datetime.datetime.utcnow()
        return dict(
            area_vertices=self._isa.footprint.to_vertices(),
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
