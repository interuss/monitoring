import re
from datetime import datetime, timedelta
from typing import Dict, Any, List

import s2sphere

from monitoring.monitorlib.fetch.rid import Subscription
from monitoring.monitorlib.mutate.rid import ChangedSubscription
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources import VerticesResource
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import (
    GenericTestScenario,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext

TIME_TOLERANCE_SEC = 1


class SubscriptionSimple(GenericTestScenario):
    """Based on prober/rid/v2/test_subscription_simple.py from the legacy prober tool."""

    SUB_TYPE = register_resource_type(371, "Subscription")

    # Base identifier for the subscriptions that will be created
    _base_sub_id: str

    # The value for 'owner' we'll expect the DSS to set on subscriptions
    _client_identity: ClientIdentityResource

    _test_subscription_ids: List[str]

    # Base parameters used for subscription creation variations
    _default_creation_params: Dict[str, Any]

    # Effective parameters used for each subscription, indexed by subscription ID
    _sub_params_by_sub_id: Dict[str, Dict[str, Any]]

    # Keep track of the latest subscription returned by the DSS
    _current_subscriptions: Dict[str, Subscription]

    # An area designed to be too big to be allowed to search by the DSS
    _problematically_big_area: List[s2sphere.LatLng]

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        isa: ServiceAreaResource,
        problematically_big_area: VerticesResource,
        client_identity: ClientIdentityResource,
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
        self._base_sub_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._isa = isa.specification
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]
        # List of vertices that has the same first and last point:
        # Used to validate some special-case handling by the DSS
        self._isa_area_loop = self._isa_area.copy()
        self._isa_area_loop.append(self._isa_area_loop[0])

        # Prepare 4 different subscription ids:
        self._test_subscription_ids = [
            self._base_sub_id[:-1] + f"{i}" for i in range(4)
        ]

        self._default_creation_params = self._isa.get_new_subscription_params(
            sub_id="",  # subscription ID will need to be overwritten
            # Set this slightly in the past: we will update the subscriptions
            # to a later value that still needs to be roughly 'now' without getting into the future
            start_time=datetime.now().astimezone() - timedelta(seconds=10),
            duration=timedelta(minutes=10),
        )

        self._problematically_big_area = [
            vertex.as_s2sphere()
            for vertex in problematically_big_area.specification.vertices
        ]

        self._client_identity = client_identity

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self._setup_case()
        self.begin_test_case("Subscription Simple")

        self.begin_test_step("Create subscription validation")
        self._create_and_validate_subs()
        self.end_test_step()

        self.begin_test_step("Mutate Subscription")
        self._test_mutate_subscriptions_shift_time()
        self._test_mutate_subscriptions_change_area()
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

        # Multiple runs of the scenario seem to rely on the same instance of it:
        # thus we need to reset the state of the scenario before running it.
        self._current_subscriptions = {}
        self._sub_params_by_sub_id = {}

        self._ensure_clean_workspace_step()

        self.end_test_case()

    def _ensure_clean_workspace_step(self):
        self.begin_test_step("Ensure clean workspace")
        # Start by dropping any active sub
        self._ensure_no_active_subs_exist()
        # Check for subscriptions that will collide with our IDs and drop them
        self._ensure_test_sub_ids_do_not_exist()
        self.end_test_step()

    def _ensure_test_sub_ids_do_not_exist(self):
        """
        Ensures no subscription with the IDs we intend to use exist.
        Note that expired subscriptions won't appear in searches,
        which is why we need to explicitly test for their presence.
        """
        for sub_id in self._test_subscription_ids:
            self._dss_wrapper.cleanup_sub(sub_id)

    def _ensure_no_active_subs_exist(self):
        """Ensure that we don't currently have any other active subscriptions at the DSS:
        as there is a limit on how many simultaneous subscriptions we can create,
        we want to avoid potentially reaching the limit during this scenario."""

        with self.check(
            "Successful subscription search query",
            [self._dss_wrapper.participant_id],
        ) as check:
            subs_in_area = self._dss_wrapper.search_subs(
                check,
                self._isa_area,
            )

        for sub_id, sub in subs_in_area.subscriptions.items():
            with self.check(
                "Subscription can be deleted", [self._dss_wrapper.participant_id]
            ) as check:
                self._dss_wrapper.del_sub(check, sub_id, sub.version)

    def _create_and_validate_subs(self):
        """
        Creates multiple subscriptions using the configured footprint and variants of undefined start and end time parameters:

         - no start and end time
         - no start time, with end time
         - with start time, no end time
         - with both start and end time

        Note that this does not check for service areas in the response: this behavior is checked
        in the isa_subscription_interactions scenario.

        When this function returns, four subscriptions are expected to be created at the DSS
        """

        # Create the subscription without start and end time
        no_opt_params = self._default_creation_params.copy()
        no_opt_params["sub_id"] = self._test_subscription_ids[0]
        no_opt_params["start_time"] = None
        no_opt_params["end_time"] = None
        self._create_sub_with_params(no_opt_params)

        # Create the subscription with only end time set
        no_start_param = self._default_creation_params.copy()
        no_start_param["sub_id"] = self._test_subscription_ids[1]
        no_start_param["start_time"] = None
        self._create_sub_with_params(no_start_param)

        # Create the subscription with only start time set
        no_end_param = self._default_creation_params.copy()
        no_end_param["sub_id"] = self._test_subscription_ids[2]
        no_end_param["end_time"] = None
        self._create_sub_with_params(no_end_param)

        # Create the subscription with all parameters set:
        all_set_params = self._default_creation_params.copy()
        all_set_params["sub_id"] = self._test_subscription_ids[3]
        self._create_sub_with_params(all_set_params)

    def _create_sub_with_params(self, creation_params: Dict[str, Any]):
        with self.check(
            "Create subscription", [self._dss_wrapper.participant_id]
        ) as check:
            newly_created = self._dss_wrapper.put_sub(
                check,
                **creation_params,
            )
        # Check that what we get back is valid and corresponds to what we want to create
        self._compare_upsert_resp_with_params(
            creation_params["sub_id"], newly_created, creation_params, False
        )

        # Check that the notification index is 0 for a newly created subscription.
        # Should the notification field be missing, we assume it will have defaulted to 0 on the DSS's side.
        with self.check(
            "Returned notification index is 0 if present",
            [self._dss_wrapper.participant_id],
        ) as check:
            notif_index = newly_created.subscription.notification_index
            if notif_index is not None and notif_index != 0:
                check.record_failed(
                    f"Returned notification index was {notif_index} instead of 0",
                    Severity.High,
                    details="A subscription is expected to have a notification index of 0 when it is created"
                    f"Parameters used: {creation_params}",
                    query_timestamps=[newly_created.query.request.timestamp],
                )

        # Store the version of the subscription
        self._current_subscriptions[
            creation_params["sub_id"]
        ] = newly_created.subscription
        # Store the parameters we used for that subscription
        self._sub_params_by_sub_id[creation_params["sub_id"]] = creation_params

    def _compare_upsert_resp_with_params(
        self,
        sub_id: str,
        creation_resp_under_test: ChangedSubscription,
        creation_params: Dict[str, Any],
        was_mutated: bool,
    ):
        """
        Verify that the response of the server is conforming to the spec and the parameters we used in the request.
        """
        check_name = (
            "Response to subscription mutation contains a subscription"
            if was_mutated
            else "Response to subscription creation contains a subscription"
        )
        with self.check(
            check_name,
            [self._dss_wrapper.participant_id],
        ) as check:
            if not creation_resp_under_test.subscription:
                check.record_failed(
                    "Response to subscription creation did not contain a subscription",
                    Severity.High,
                    details="A subscription is expected to be returned in the response to a subscription creation request."
                    f"Parameters used: {creation_params}",
                    query_timestamps=[creation_resp_under_test.query.request.timestamp],
                )

        # Make sure the subscription corresponds to what we requested
        self._validate_subscription(
            sub_id,
            creation_resp_under_test.subscription,
            creation_params,
            was_mutated=was_mutated,
            query_timestamps=[creation_resp_under_test.query.request.timestamp],
        )

    def _test_mutate_subscriptions_shift_time(self):
        """Mutate all existing subscriptions by adding 10 seconds to their start and end times"""

        for sub_id, sub in self._current_subscriptions.items():
            with self.check(
                "Subscription can be mutated", [self._dss_wrapper.participant_id]
            ) as check:
                orig_params = self._sub_params_by_sub_id[sub_id].copy()
                new_params = dict(
                    sub_id=sub_id,
                    area_vertices=orig_params["area_vertices"][
                        :-1
                    ],  # remove the last vertex to change the footprint
                    alt_lo=orig_params["alt_lo"],
                    alt_hi=orig_params["alt_hi"],
                    start_time=sub.time_start + timedelta(seconds=10),
                    end_time=sub.time_end + timedelta(seconds=10),
                    uss_base_url=orig_params["uss_base_url"],
                )
                mutated_sub_response = self._dss_wrapper.put_sub(
                    check,
                    sub_version=sub.version,
                    **new_params,
                )

            # Check that what we get back is valid and corresponds to what we want to create
            self._compare_upsert_resp_with_params(
                sub_id, mutated_sub_response, new_params, was_mutated=True
            )
            # Store the version of the subscription
            self._current_subscriptions[sub_id] = mutated_sub_response.subscription
            # Update the parameters we used for that subscription
            self._sub_params_by_sub_id[sub_id] = new_params

    def _test_mutate_subscriptions_change_area(self):
        """
        Mutate all existing subscriptions by updating their footprint.
        """
        for sub_id, sub in self._current_subscriptions.items():
            with self.check(
                "Subscription can be mutated", [self._dss_wrapper.participant_id]
            ) as check:
                new_params = self._sub_params_by_sub_id[sub_id].copy()

                # Shift all previous vertices west by 0.001 degrees
                new_params["area_vertices"] = [
                    s2sphere.LatLng.from_degrees(
                        vertex.lat().degrees, vertex.lng().degrees - 0.001
                    )
                    for vertex in new_params["area_vertices"]
                ]
                mutated_sub_response = self._dss_wrapper.put_sub(
                    check,
                    sub_version=sub.version,
                    **new_params,
                )

            # Check that what we get back is valid and corresponds to what we want to create
            self._compare_upsert_resp_with_params(
                sub_id, mutated_sub_response, new_params, was_mutated=True
            )
            # Store the version of the subscription
            self._current_subscriptions[sub_id] = mutated_sub_response.subscription
            # Update the parameters we used for that subscription
            self._sub_params_by_sub_id[sub_id] = new_params

    def _test_get_sub(self):
        """Retrieves the previously created Subscription by their ID and ensures that
        the data obtained in the response is correct."""

        for sub_id, sub_params in self._sub_params_by_sub_id.items():
            with self.check(
                "Get Subscription by ID", [self._dss_wrapper.participant_id]
            ) as check:
                fetched_sub = self._dss_wrapper.get_sub(
                    check,
                    sub_id,
                )

            # Make sure the subscription corresponds to what we requested
            self._validate_subscription_and_notif_index(
                sub_id,
                fetched_sub.subscription,
                sub_params,
                False,
                [fetched_sub.query.request.timestamp],
            )

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

        for sub_id, sub_params in self._sub_params_by_sub_id.items():
            with self.check(
                "Created Subscription is in search results",
                [self._dss_wrapper.participant_id],
            ) as check:
                if sub_id not in subs_in_area.subscriptions:
                    check.record_failed(
                        "Created subscription is not present in search results",
                        Severity.High,
                        f"The subscription {sub_id} was expected to be found in the search results, but these only contained the following subscriptions: {subs_in_area.subscriptions.keys()}",
                        query_timestamps=[subs_in_area.query.request.timestamp],
                    )

            # Make sure the returned subscription corresponds to what we created
            self._validate_subscription_and_notif_index(
                sub_id,
                subs_in_area.subscriptions[sub_id],
                sub_params,
                False,
                [subs_in_area.query.request.timestamp],
            )

    def _test_huge_area_search_sub(self):
        """Checks that too big search areas are rejected"""
        with self.check(
            "No huge search area allowed", [self._dss_wrapper.participant_id]
        ) as check:
            self._dss_wrapper.search_subs_expect_response_code(
                check=check,
                expected_codes={400, 413},
                area=self._problematically_big_area,
            )

    def _test_delete_sub_faulty(self):
        """Try to delete subscription in an incorrect way"""
        for sub_id in self._current_subscriptions.keys():
            with self.check(
                "Missing version prevents deletion", [self._dss_wrapper.participant_id]
            ) as check:
                self._dss_wrapper.del_sub_expect_response_code(
                    check=check,
                    expected_response_codes={400},
                    sub_id=sub_id,
                    sub_version="",  # this results in an empty url path parameter in the query (what we want to test)
                )

            with self.check(
                "Incorrect version prevents deletion",
                [self._dss_wrapper.participant_id],
            ) as check:
                self._dss_wrapper.del_sub_expect_response_code(
                    check=check,
                    expected_response_codes={400},
                    sub_id=sub_id,
                    sub_version="notacorrectversion",
                )

    def _test_delete_sub(self):
        """Delete the subscriptions in the correct way"""

        for sub_id, sub in self._current_subscriptions.items():
            with self.check(
                "Subscription can be deleted", [self._dss_wrapper.participant_id]
            ) as check:
                deleted_sub = self._dss_wrapper.del_sub(
                    check=check, sub_id=sub_id, sub_version=sub.version
                )
            # Make sure the returned subscription corresponds to what we created
            self._validate_subscription_and_notif_index(
                sub_id,
                deleted_sub.subscription,
                self._sub_params_by_sub_id[sub_id],
                False,
                [deleted_sub.query.request.timestamp],
            )

        self._current_subscriptions = {}

    def _test_get_deleted_sub(self):
        """Try to retrieve the deleted subscription by its ID."""
        for sub_id in self._sub_params_by_sub_id.keys():
            with self.check(
                "Query by subscription ID should fail",
                [self._dss_wrapper.participant_id],
            ) as check:
                self._dss_wrapper.get_sub_expect_response_code(
                    check=check,
                    expected_response_codes={404},
                    sub_id=sub_id,
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
            for sub_id in self._sub_params_by_sub_id.keys():
                if sub_id in subs_in_area.subscriptions:
                    check.record_failed(
                        "A deleted subscription is still present in search results",
                        Severity.High,
                        f"The subscription {sub_id} was deleted, and thus not expected to be found in the search results."
                        f"Subscription IDs returned in search results: {subs_in_area.subscriptions.keys()}",
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

    def _validate_subscription_and_notif_index(
        self,
        sub_id: str,
        sub_under_test: Subscription,
        creation_params: Dict[str, Any],
        was_mutated: bool,
        query_timestamps: List[datetime],
    ):
        """Compare the passed subscription with the data we specified when creating it"""
        self._validate_subscription(
            sub_id, sub_under_test, creation_params, was_mutated, query_timestamps
        )

        # Check the notification index is 0 or more, if it is present
        # (notifications might have been sent out between the creation and subsequent query)
        # Should the index be absent, we assume it to be 0 on the DSS's side.
        with self.check(
            "Returned notification index is equal to or greater than 0",
            [self._dss_wrapper.participant_id],
        ) as check:
            if (
                sub_under_test.notification_index is not None
                and sub_under_test.notification_index < 0
            ):
                check.record_failed(
                    "Returned notification index is lower than 0",
                    Severity.High,
                    f"Returned: {sub_under_test.notification_index} when 0 or more was expected"
                    f"Parameters used: {creation_params}",
                    query_timestamps=query_timestamps,
                )

    def _validate_subscription(
        self,
        sub_id: str,
        sub_under_test: Subscription,
        creation_params: Dict[str, Any],
        was_mutated: bool,
        query_timestamps: List[datetime],
    ):
        """
        Validate the subscription against the parameters used to create it.

        Args:
            sub_id: ID of the subscription being validated
            sub_under_test: subscription being validated
            creation_params: parameters used to create or update the subscription
            was_mutated: true if the resulting subscription is the result of a mutation or deletion
        """

        expect_start_time = creation_params["start_time"]
        expect_end_time = creation_params["end_time"]

        with self.check(
            "Returned subscription has an ID", [self._dss_wrapper.participant_id]
        ) as check:
            if not sub_under_test.id:
                check.record_failed(
                    "Returned subscription had no ID",
                    Severity.High,
                    details="A subscription is expected to have an ID",
                    query_timestamps=query_timestamps,
                )

        with self.check(
            "Returned subscription ID is correct", [self._dss_wrapper.participant_id]
        ) as check:
            if sub_under_test.id != sub_id:
                check.record_failed(
                    "Returned subscription ID does not match provided one",
                    Severity.High,
                    f"Provided: {sub_id}, Returned: {sub_under_test.id}",
                    query_timestamps=query_timestamps,
                )

        with self.check(
            "Returned subscription has an owner", [self._dss_wrapper.participant_id]
        ) as check:
            if not sub_under_test.owner:
                check.record_failed(
                    "Returned subscription had no owner",
                    Severity.High,
                    details="A subscription is expected to have an owner",
                    query_timestamps=query_timestamps,
                )

        with self.check(
            "Returned subscription owner is correct", [self._dss_wrapper.participant_id]
        ) as check:
            client_sub = self._client_identity.subscriber()
            if sub_under_test.owner != client_sub:
                check.record_failed(
                    "Returned subscription owner does not match provided one",
                    Severity.High,
                    f"Provided: {client_sub}, Returned: {sub_under_test.owner}",
                    query_timestamps=query_timestamps,
                )

        with self.check(
            "Returned subscription has an ISA URL", [self._dss_wrapper.participant_id]
        ) as check:
            if not sub_under_test.isa_url:
                check.record_failed(
                    "Returned subscription had no ISA URL",
                    Severity.High,
                    details="A subscription is expected to have an ISA URL",
                    query_timestamps=query_timestamps,
                )

        with self.check(
            "Returned ISA URL has correct base URL", [self._dss_wrapper.participant_id]
        ) as check:
            if not sub_under_test.isa_url.startswith(self._isa.base_url):
                check.record_failed(
                    "Returned USS Base URL does not match provided one",
                    Severity.High,
                    f"Provided: {self._isa.base_url}, Returned: {sub_under_test.isa_url}",
                    query_timestamps=query_timestamps,
                )

        with self.check(
            "Returned subscription has a start time", [self._dss_wrapper.participant_id]
        ) as check:
            if not sub_under_test.time_start:
                check.record_failed(
                    "Returned subscription had no start time",
                    Severity.High,
                    details="A subscription is expected to have a start time",
                    query_timestamps=query_timestamps,
                )

        with self.check(
            "Returned subscription has an end time", [self._dss_wrapper.participant_id]
        ) as check:
            if not sub_under_test.time_end:
                check.record_failed(
                    "Returned subscription had no end time",
                    Severity.High,
                    details="A subscription is expected to have an end time",
                    query_timestamps=query_timestamps,
                )

        # When expect_start_time has not been defined, there is no clear specification on
        # what the returned start time should be, so we only check it when we have requested one
        if expect_start_time is not None:
            with self.check(
                "Returned start time is correct", [self._dss_wrapper.participant_id]
            ) as check:
                if (
                    abs(sub_under_test.time_start - expect_start_time).total_seconds()
                    > TIME_TOLERANCE_SEC
                ):
                    check.record_failed(
                        "Returned start time does not match provided one",
                        Severity.High,
                        f"Provided: {expect_start_time}, Returned: {sub_under_test.time_start}",
                        query_timestamps=query_timestamps,
                    )

        # When expect_end_time has not been defined, there is no clear specification on
        # what the returned end time should be, so we only check it when we have requested one
        if expect_end_time is not None:
            with self.check(
                "Returned end time is correct", [self._dss_wrapper.participant_id]
            ) as check:
                if (
                    abs(sub_under_test.time_end - expect_end_time).total_seconds()
                    > TIME_TOLERANCE_SEC
                ):
                    check.record_failed(
                        "Returned end time does not match provided one",
                        Severity.High,
                        f"Provided: {expect_end_time}, Returned: {sub_under_test.time_end}",
                        query_timestamps=query_timestamps,
                    )

        with self.check(
            "Returned subscription has a version", [self._dss_wrapper.participant_id]
        ) as check:
            if not sub_under_test.version:
                check.record_failed(
                    "Returned subscription had no version",
                    Severity.High,
                    details="A subscription is expected to have a version",
                    query_timestamps=query_timestamps,
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
                    query_timestamps=query_timestamps,
                )

        # If the subscription was mutated, we compare the returned version with the previously stored one:
        if was_mutated:
            with self.check(
                "Mutated subscription version is updated",
                [self._dss_wrapper.participant_id],
            ) as check:
                if (
                    sub_under_test.version
                    == self._current_subscriptions[sub_under_test.id]
                ):
                    check.record_failed(
                        "Returned subscription version was not updated",
                        Severity.High,
                        f"Returned: {sub_under_test.version}, Expected: {self._current_subscriptions[sub_under_test.id]}",
                        query_timestamps=query_timestamps,
                    )
        elif sub_id in self._current_subscriptions.keys():
            with self.check(
                "Non-mutated subscription keeps the same version",
                [self._dss_wrapper.participant_id],
            ) as check:
                if (
                    sub_under_test.version
                    != self._current_subscriptions[sub_under_test.id].version
                ):
                    check.record_failed(
                        "Returned subscription version was updated",
                        Severity.High,
                        f"Returned: {sub_under_test.version}, Expected: {self._current_subscriptions[sub_under_test.id]}.",
                        query_timestamps=query_timestamps,
                    )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_test_sub_ids_do_not_exist()
        self.end_cleanup()
