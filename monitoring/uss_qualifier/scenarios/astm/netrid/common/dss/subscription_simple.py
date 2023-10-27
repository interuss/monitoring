import re
from datetime import datetime, timedelta
from typing import Dict, Any, List

import s2sphere

from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources import VerticesResource
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import (
    GenericTestScenario,
)

TIME_TOLERANCE_SEC = 1


class SubscriptionSimple(GenericTestScenario):
    """Based on prober/rid/v2/test_subscription_simple.py from the legacy prober tool."""

    SUB_TYPE = register_resource_type(371, "Subscription")

    _test_subscription_params: Dict[str, Any]
    _problematically_big_area: List[s2sphere.LatLng]

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        isa: ServiceAreaResource,
        problematically_big_area: VerticesResource,
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
        self._sub_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._isa = isa.specification
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]
        # List of vertices that has the same first and last point:
        # Used to validate some special-case handling by the DSS
        self._isa_area_loop = self._isa_area.copy()
        self._isa_area_loop.append(self._isa_area_loop[0])

        self._test_subscription_params = self._isa.get_new_subscription_params(
            sub_id=self._sub_id,
            start_time=datetime.now().astimezone(),
            duration=timedelta(
                minutes=5
            ),  # 5 minutes are enough to run through this test
        )

        self._problematically_big_area = [
            vertex.as_s2sphere()
            for vertex in problematically_big_area.specification.vertices
        ]

    def run(self):
        self.begin_test_scenario()

        self._setup_case()

        self.begin_test_case("Subscription Simple")

        self.begin_test_step("Create subscription validation")

        self._create_and_validate_sub()

        self.end_test_step()
        self.begin_test_step("Query Existing Subscription")

        self._test_get_sub()
        self._test_valid_search_sub()
        self._test_huge_area_search_sub()

        self.end_test_step()
        self.begin_test_step("Delete Subscription")

        self._test_delete_sub_faulty()
        self._test_delete_sub()

        self.end_test_step()
        self.begin_test_step("Query Deleted Subscription")

        self._test_get_deleted_sub()
        self._test_search_deleted_sub()
        self._test_loop_vertices_search_deleted_sub()

        self.end_test_step()
        self.end_test_case()

        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")

        self._ensure_clean_workspace_step()

        self.end_test_case()

    def _ensure_clean_workspace_step(self):
        self.begin_test_step("Ensure clean workspace")
        self._ensure_test_sub_does_not_exist()
        self.end_test_step()

    def _ensure_test_sub_does_not_exist(self):
        with self.check(
            "Ensure subscription with test ID does not exist",
            [self._dss_wrapper.participant_id],
        ) as check:
            self._dss_wrapper.cleanup_sub(check, self._sub_id)

    def _create_and_validate_sub(self):
        """Creates a subscription and ensures that the data obtained in the response is correct.
        Note that this does not check for services areas in the response: this behavior is checked
        in the isa_subscription_interactions scenario.
        """
        with self.check(
            "Create subscription", [self._dss_wrapper.participant_id]
        ) as check:
            created_sub = self._dss_wrapper.put_sub(
                check,
                **self._test_subscription_params,
            )

        # Make sure the subscription corresponds to what we requested
        self._validate_subscription(created_sub.subscription)

        # Check the notification index is 0
        with self.check(
            "Returned notification index is 0", [self._dss_wrapper.participant_id]
        ) as check:
            notif_index = created_sub.subscription.notification_index
            if notif_index != 0:
                check.record_failed(
                    f"Returned notification index was {notif_index} instead of 0",
                    Severity.High,
                    query_timestamps=[created_sub.query.request.timestamp],
                )

        self._current_sub_version = created_sub.subscription.version

    def _test_get_sub(self):
        """Retrieves the previously created Submission by its ID and ensures that
        the data obtained in the response is correct."""
        with self.check(
            "Get Subscription by ID", [self._dss_wrapper.participant_id]
        ) as check:
            fetched_sub = self._dss_wrapper.get_sub(
                check,
                self._sub_id,
            )

        # Make sure the subscription corresponds to what we requested
        self._validate_subscription_and_notif_index(fetched_sub.subscription)

    def _test_valid_search_sub(self):
        """Search for the created subscription by using the configured ISA's footprint. This is expected to work"""

        with self.check(
            "Search for all subscriptions in ISA area",
            [self._dss_wrapper.participant_id],
        ) as check:
            subs_in_area = self._dss_wrapper.search_subs(
                check,
                self._isa_area,
            )

        with self.check(
            "Created Subscription is in search results",
            [self._dss_wrapper.participant_id],
        ) as check:
            if self._sub_id not in subs_in_area.subscriptions:
                check.record_failed(
                    "Created subscription is not present in search results",
                    Severity.High,
                    f"The subscription {self._sub_id} was expected to be found in the search results, but these only contained the following subscriptions: {subs_in_area.subscriptions.keys()}",
                    query_timestamps=[subs_in_area.query.request.timestamp],
                )

        # Make sure the returned subscription corresponds to what we created
        self._validate_subscription_and_notif_index(
            subs_in_area.subscriptions[self._sub_id]
        )

    def _test_huge_area_search_sub(self):
        """Checks that too big search areas are rejected"""
        with self.check(
            "No huge search area allowed", [self._dss_wrapper.participant_id]
        ) as check:
            self._dss_wrapper.search_subs_expect_response_code(
                check=check,
                expected_codes={413},
                area=self._problematically_big_area,
            )

    def _test_delete_sub_faulty(self):
        """Try to delete subscription in an incorrect way"""
        with self.check(
            "Missing version prevents deletion", [self._dss_wrapper.participant_id]
        ) as check:
            self._dss_wrapper.del_sub_expect_response_code(
                check=check,
                expected_response_codes={400},
                sub_id=self._sub_id,
                sub_version="",  # this results in an empty url path parameter in the query (what we want to test)
            )

        with self.check(
            "Incorrect version prevents deletion", [self._dss_wrapper.participant_id]
        ) as check:
            self._dss_wrapper.del_sub_expect_response_code(
                check=check,
                expected_response_codes={400},
                sub_id=self._sub_id,
                sub_version="notacorrectversion",
            )

    def _test_delete_sub(self):
        """Delete the subscription in the correct way"""
        with self.check(
            "Subscription can be deleted", [self._dss_wrapper.participant_id]
        ) as check:
            deleted_sub = self._dss_wrapper.del_sub(
                check=check, sub_id=self._sub_id, sub_version=self._current_sub_version
            )

        # Make sure the returned subscription corresponds to what we created
        self._validate_subscription_and_notif_index(deleted_sub.subscription)

    def _test_get_deleted_sub(self):
        """Try to retrieve the deleted subscription by its ID."""
        with self.check(
            "Query by subscription ID should fail", [self._dss_wrapper.participant_id]
        ) as check:
            self._dss_wrapper.get_sub_expect_response_code(
                check=check,
                expected_response_codes={404},
                sub_id=self._sub_id,
            )

    def _test_search_deleted_sub(self):
        """Try searching for the deleted subscription"""
        # Search should succeed
        with self.check(
            "Search for all subscriptions in ISA area",
            [self._dss_wrapper.participant_id],
        ) as check:
            subs_in_area = self._dss_wrapper.search_subs(
                check,
                self._isa_area,
            )

        with self.check(
            "Deleted subscription should not be present in search results",
            [self._dss_wrapper.participant_id],
        ) as check:
            if self._sub_id in subs_in_area.subscriptions:
                check.record_failed(
                    "Deleted subscription is still present in search results",
                    Severity.High,
                    f"The subscription {self._sub_id} was deleted, and thus not expected to be found in the search results.",
                    query_timestamps=[subs_in_area.query.request.timestamp],
                )

    def _test_loop_vertices_search_deleted_sub(self):
        """Try searching for the deleted subscription using vertices that describe a loop"""
        with self.check(
            "Search area that represents a loop is not allowed",
            [self._dss_wrapper.participant_id],
        ) as check:
            self._dss_wrapper.search_subs_expect_response_code(
                check=check,
                expected_codes={400},  # We explicitly want to forbid a 500 error here
                area=self._isa_area_loop,
            )

    def _validate_subscription_and_notif_index(self, sub_under_test):
        """Compare the passed subscription with the data we specified when creating it"""
        self._validate_subscription(sub_under_test)

        # Check the notification index is 0 or more
        # (notifications might have been sent out between the creation and subsequent query)
        with self.check(
            "Returned notification index is equal to or greater than 0",
            [self._dss_wrapper.participant_id],
        ) as check:
            if sub_under_test.notification_index < 0:
                check.record_failed(
                    "Returned notification index is lower than 0",
                    Severity.High,
                    f"Returned: {sub_under_test.notification_index} when 0 or more was expected",
                    query_timestamps=[sub_under_test.query.request.timestamp],
                )

    def _validate_subscription(self, sub_under_test):

        with self.check(
            "Returned subscription ID is correct", [self._dss_wrapper.participant_id]
        ) as check:
            if sub_under_test.id != self._sub_id:
                check.record_failed(
                    "Returned subscription ID does not match provided one",
                    Severity.High,
                    f"Provided: {self._sub_id}, Returned: {sub_under_test.id}",
                    query_timestamps=[sub_under_test.query.request.timestamp],
                )

        with self.check(
            "Returned ISA URL has correct base URL", [self._dss_wrapper.participant_id]
        ) as check:
            if not sub_under_test.isa_url.startswith(self._isa.base_url):
                check.record_failed(
                    "Returned USS Base URL does not match provided one",
                    Severity.High,
                    f"Provided: {self._isa.base_url}, Returned: {sub_under_test.isa_url}",
                    query_timestamps=[sub_under_test.query.request.timestamp],
                )

        with self.check(
            "Returned start time is correct", [self._dss_wrapper.participant_id]
        ) as check:
            if (
                abs(
                    sub_under_test.time_start
                    - self._test_subscription_params["start_time"]
                ).total_seconds()
                > TIME_TOLERANCE_SEC
            ):
                check.record_failed(
                    "Returned start time does not match provided one",
                    Severity.High,
                    f"Provided: {self._test_subscription_params['time_start']}, Returned: {sub_under_test.time_start}",
                    query_timestamps=[sub_under_test.query.request.timestamp],
                )

        with self.check(
            "Returned end time is correct", [self._dss_wrapper.participant_id]
        ) as check:
            if (
                abs(
                    sub_under_test.time_end - self._test_subscription_params["end_time"]
                ).total_seconds()
                > TIME_TOLERANCE_SEC
            ):
                check.record_failed(
                    "Returned end time does not match provided one",
                    Severity.High,
                    f"Provided: {self._test_subscription_params['time_end']}, Returned: {sub_under_test.time_end}",
                    query_timestamps=[sub_under_test.query.request.timestamp],
                )

        with self.check(
            "Generated subscription version has proper format",
            [self._dss_wrapper.participant_id],
        ) as check:
            if not re.match(r"[a-z0-9]{10,}$", sub_under_test.version):
                check.record_failed(
                    "Returned subscription version does not match expected format",
                    Severity.High,
                    f"Returned: {sub_under_test.version}, this does not match"
                    + "[a-z0-9]{10,}$",
                    query_timestamps=[sub_under_test.query.request.timestamp],
                )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_test_sub_does_not_exist()
        self.end_cleanup()
