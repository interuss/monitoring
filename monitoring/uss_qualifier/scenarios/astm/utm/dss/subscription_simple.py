from datetime import datetime, timedelta
from typing import Dict, List

from uas_standards.astm.f3548.v21.api import Subscription, SubscriptionID
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib import geo
from monitoring.monitorlib.geo import Polygon, Volume3D
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources import VerticesResource
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.planning_area import (
    SubscriptionParams,
)
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.sub.crud import (
    sub_create_query,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.validators.subscription_validator import (
    SubscriptionValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

TIME_TOLERANCE_SEC = 1
"""tolerance when comparing created vs returned timestamps"""

LONGITUDE_MUTATION_SHIFT = 0.001
"""Amount of degrees by which the longitude will be shifted when subscriptions are mutated"""


class SubscriptionSimple(TestScenario):
    """
    A scenario that tests basic operations on SCD Subscriptions:

      - create several subscriptions with a combination of missing optional parameters
      - check the subscriptions can be retrieved by ID and searched for
      - mutate the subscriptions
      - delete the subscriptions
      - confirm they have been deleted
    """

    SUB_TYPE = register_resource_type(377, "Subscription")

    # Base identifier for the subscriptions that will be created
    _base_sub_id: SubscriptionID

    _test_subscription_ids: List[SubscriptionID]

    # Base parameters used for subscription creation variations
    _sub_generation_params: SubscriptionParams

    # Effective parameters used for each subscription, indexed by subscription ID
    _sub_params_by_sub_id: Dict[SubscriptionID, SubscriptionParams]

    # Keep track of the latest subscription returned by the DSS
    _current_subscriptions: Dict[SubscriptionID, Subscription]

    # An area designed to be too big to be allowed to search by the DSS
    _problematically_big_area_vol: Polygon

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        planning_area: PlanningAreaResource,
        problematically_big_area: VerticesResource,
    ):
        """
        Args:
            dss: dss to test
            id_generator: will let us generate specific identifiers
            planning_area: An Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.
            problematically_big_area: An area that is too big to be searched for on the DSS
        """
        super().__init__()
        scopes = {Scope.StrategicCoordination: "create and delete subscriptions"}
        # This is an UTMClientSession
        self._dss = dss.get_instance(scopes)
        self._pid = [self._dss.participant_id]
        self._base_sub_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._planning_area = planning_area.specification

        # Build a ready-to-use 4D volume with no specified time for searching
        # the currently active subscriptions
        self._planning_area_volume4d = Volume4D(
            volume=self._planning_area.volume,
        )

        # Prepare 4 different subscription ids:
        self._test_subscription_ids = [
            self._base_sub_id[:-1] + f"{i}" for i in range(4)
        ]

        self._problematically_big_area_vol = Polygon(
            vertices=problematically_big_area.specification.vertices
        )

        self._current_subscriptions = {}
        self._sub_params_by_sub_id = {}

    def _build_current_time_sub_params(self):
        return self._planning_area.get_new_subscription_params(
            subscription_id="",  # subscription ID will need to be overwritten
            # Set this slightly in the past: we will update the subscriptions
            # to a later value that still needs to be roughly 'now' without getting into the future
            start_time=datetime.now().astimezone() - timedelta(seconds=10),
            duration=timedelta(minutes=45),
            # This is a planning area without constraint processing
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self._setup_case()
        self.begin_test_case("Subscription Simple")

        self.begin_test_step("Create subscription validation")
        self._create_and_validate_subs()
        self.end_test_step()

        self.begin_test_step("Attempt Subscription mutation with incorrect version")
        self._test_mutate_subscription_version_check()
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
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")

        self._sub_generation_params = self._build_current_time_sub_params()

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
            test_step_fragments.cleanup_sub(self, self._dss, sub_id)

    def _ensure_no_active_subs_exist(self):
        test_step_fragments.cleanup_active_subs(
            self,
            self._dss,
            self._planning_area_volume4d,
        )

    def _create_and_validate_subs(self):
        """
        Creates multiple subscriptions using the configured footprint and variants of undefined start and end time parameters:

         - no start and end time
         - no start time, with end time
         - with start time, no end time
         - with both start and end time

        When this function returns, four subscriptions are expected to be created at the DSS
        """

        # Create the subscription without start and end time
        no_opt_params = self._sub_generation_params.copy()
        no_opt_params.sub_id = self._test_subscription_ids[0]
        no_opt_params.start_time = None
        no_opt_params.end_time = None
        self._create_sub_with_params(no_opt_params)

        # Create the subscription with only end time set
        no_start_param = self._sub_generation_params.copy()
        no_start_param.sub_id = self._test_subscription_ids[1]
        no_start_param.start_time = None
        self._create_sub_with_params(no_start_param)

        # Create the subscription with only start time set
        no_end_param = self._sub_generation_params.copy()
        no_end_param.sub_id = self._test_subscription_ids[2]
        no_end_param.end_time = None
        self._create_sub_with_params(no_end_param)

        # Create the subscription with all parameters set:
        all_set_params = self._sub_generation_params.copy()
        all_set_params.sub_id = self._test_subscription_ids[3]
        self._create_sub_with_params(all_set_params)

    def _create_sub_with_params(self, creation_params: SubscriptionParams):
        _, _, newly_created = sub_create_query(self, self._dss, creation_params)

        with self.check(
            "Create subscription response content is correct", self._pid
        ) as check:
            SubscriptionValidator(
                check,
                self,
                self._pid,
                creation_params,
            ).validate_created_subscription(creation_params.sub_id, newly_created)

        # Store the subscription
        self._current_subscriptions[creation_params.sub_id] = newly_created.subscription
        # Store the parameters we used for that subscription
        self._sub_params_by_sub_id[creation_params.sub_id] = creation_params

    def _compare_upsert_resp_with_params(
        self,
        sub_id: str,
        creation_resp_under_test: MutatedSubscription,
        creation_params: SubscriptionParams,
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
            self._pid,
        ) as check:
            if not creation_resp_under_test.subscription:
                check.record_failed(
                    "Response to subscription creation did not contain a subscription",
                    details="A subscription is expected to be returned in the response to a subscription creation request."
                    f"Parameters used: {creation_params}",
                    query_timestamps=[creation_resp_under_test.request.timestamp],
                )

        # Make sure the subscription corresponds to what we requested
        self._validate_subscription(
            sub_id,
            creation_resp_under_test.subscription,
            creation_params,
            was_mutated=was_mutated,
            query_timestamps=[creation_resp_under_test.request.timestamp],
        )

    def _test_mutate_subscription_version_check(self):
        """Attempt to mutate a subscription while providing a missing and incorrect OVN"""
        orig_params = self._sub_params_by_sub_id[self._base_sub_id].copy()
        sub = self._current_subscriptions[self._base_sub_id]
        new_params = SubscriptionParams(
            sub_id=self._base_sub_id,
            area_vertices=orig_params.area_vertices,
            min_alt_m=orig_params.min_alt_m,
            max_alt_m=orig_params.max_alt_m,
            start_time=sub.time_start.value.datetime + timedelta(seconds=10),
            end_time=sub.time_end.value.datetime + timedelta(seconds=10),
            base_url=orig_params.base_url,
            notify_for_op_intents=orig_params.notify_for_op_intents,
            notify_for_constraints=orig_params.notify_for_constraints,
        )

        with self.check("Mutation with empty version fails", self._pid) as check:
            no_version_res = self._dss.upsert_subscription(
                version="",
                **new_params,
            )
            if no_version_res.status_code not in [400, 409]:
                check.record_failed(
                    "Mutation with empty version did not fail as expected",
                    details=f"Mutation with an empty version is expected , received status code {no_version_res.status_code}",
                    query_timestamps=[no_version_res.request.timestamp],
                )

        with self.check("Mutation with incorrect version fails", self._pid) as check:
            wrong_version_res = self._dss.upsert_subscription(
                version="ThisIsAnIncorrectVersion",
                **new_params,
            )
            if wrong_version_res.status_code not in [400, 409]:
                check.record_failed(
                    "Mutation with incorrect version did not fail as expected",
                    details=f"Mutation with an incorrect version is expected , received status code {wrong_version_res.status_code}",
                    query_timestamps=[wrong_version_res.request.timestamp],
                )

    def _test_mutate_subscriptions_shift_time(self):
        """Mutate all existing subscriptions by adding 10 seconds to their start and end times"""

        for sub_id, sub in self._current_subscriptions.items():
            orig_params = self._sub_params_by_sub_id[sub_id].copy()
            new_params = SubscriptionParams(
                sub_id=sub_id,
                area_vertices=orig_params.area_vertices,
                min_alt_m=orig_params.min_alt_m,
                max_alt_m=orig_params.max_alt_m,
                start_time=sub.time_start.value.datetime + timedelta(seconds=10),
                end_time=sub.time_end.value.datetime + timedelta(seconds=10),
                base_url=orig_params.base_url,
                notify_for_op_intents=orig_params.notify_for_op_intents,
                notify_for_constraints=orig_params.notify_for_constraints,
            )
            mutated_sub_response = self._dss.upsert_subscription(
                version=sub.version,
                **new_params,
            )
            self.record_query(mutated_sub_response)
            with self.check("Mutate subscription query succeeds", self._pid) as check:
                if mutated_sub_response.status_code != 200:
                    check.record_failed(
                        "Subscription mutation failed",
                        details=f"Subscription mutation failed with status code {mutated_sub_response.status_code}",
                        query_timestamps=[mutated_sub_response.request.timestamp],
                    )

            with self.check(
                "Mutate subscription response is correct", self._pid
            ) as check:
                SubscriptionValidator(
                    check, self, self._pid, new_params
                ).validate_mutated_subscription(
                    sub_id,
                    mutated_sub_response,
                    self._current_subscriptions[sub_id].version,
                    False,
                )

            # Store the subscription
            self._current_subscriptions[sub_id] = mutated_sub_response.subscription
            # Update the parameters we used for that subscription
            self._sub_params_by_sub_id[sub_id] = new_params

    def _test_mutate_subscriptions_change_area(self):
        """
        Mutate all existing subscriptions by updating their footprint.
        """
        for sub_id, sub in self._current_subscriptions.items():

            new_params = self._sub_params_by_sub_id[sub_id].copy()

            # Shift all previous vertices west by 0.001 degrees
            new_params.area_vertices = geo.shift_rect_lng(
                new_params.area_vertices, LONGITUDE_MUTATION_SHIFT
            )
            mutated_sub_response = self._dss.upsert_subscription(
                version=sub.version,
                **new_params,
            )
            self.record_query(mutated_sub_response)
            with self.check("Mutate subscription query succeeds", self._pid) as check:
                if not mutated_sub_response.success:
                    check.record_failed(
                        "Subscription mutation failed",
                        details=f"Subscription mutation failed with status code {mutated_sub_response.status_code}",
                        query_timestamps=[mutated_sub_response.request.timestamp],
                    )

            with self.check(
                "Mutate subscription response is correct", self._pid
            ) as check:
                SubscriptionValidator(
                    check, self, self._pid, new_params
                ).validate_mutated_subscription(
                    sub_id,
                    mutated_sub_response,
                    self._current_subscriptions[sub_id].version,
                    False,
                )

            # Store the subscription
            self._current_subscriptions[sub_id] = mutated_sub_response.subscription
            # Update the parameters we used for that subscription
            self._sub_params_by_sub_id[sub_id] = new_params

    def _test_get_sub(self):
        """Retrieves the previously created Subscription by their ID and ensures that
        the data obtained in the response is correct."""

        for sub_id, sub_params in self._sub_params_by_sub_id.items():
            fetched_sub = self._dss.get_subscription(sub_id)
            self.record_query(fetched_sub)
            with self.check("Get subscription query succeeds", self._pid) as check:
                if not (fetched_sub.success or fetched_sub.was_not_found):
                    check.record_failed(
                        "Get subscription by ID failed",
                        details=f"Get subscription by ID failed with status code {fetched_sub.status_code}",
                        query_timestamps=[fetched_sub.request.timestamp],
                    )

            with self.check("Get subscription response is correct", self._pid) as check:
                SubscriptionValidator(
                    check, self, self._pid, sub_params
                ).validate_fetched_subscription(
                    sub_id,
                    fetched_sub,
                    self._current_subscriptions[sub_id].version,
                    False,
                )

    def _test_valid_search_sub(self):
        """Search for the created subscription by using the configured planning area's footprint. This is expected to work"""

        subs_in_area = self._dss.query_subscriptions(self._planning_area_volume4d)
        self.record_query(subs_in_area)
        with self.check(
            "Search for all subscriptions in planning area query succeeds",
            self._pid,
        ) as check:
            if subs_in_area.status_code != 200:
                check.record_failed(
                    "Search for subscriptions in planning area failed",
                    details=f"Search for subscriptions in planning area failed with status code {subs_in_area.status_code}",
                    query_timestamps=[subs_in_area.request.timestamp],
                )

        for sub_id, sub_params in self._sub_params_by_sub_id.items():
            with self.check(
                "Search for all subscriptions in planning area response is correct",
                self._pid,
            ) as check:
                SubscriptionValidator(
                    check, self, self._pid, sub_params
                ).validate_searched_subscription(
                    sub_id,
                    subs_in_area,
                    self._current_subscriptions[sub_id].version,
                    False,
                )

    def _test_huge_area_search_sub(self):
        """Checks that too big search areas are rejected"""
        invalid_search = self._dss.query_subscriptions(
            volume=Volume4D(
                volume=Volume3D(outline_polygon=self._problematically_big_area_vol)
            )
        )
        self.record_query(invalid_search)
        with self.check("No huge search area allowed", self._pid) as check:
            if invalid_search.status_code not in [400, 413]:
                check.record_failed(
                    "Search for subscriptions in huge area did not fail",
                    details=f"Search for subscriptions in huge area failed with status code {invalid_search.status_code}",
                    query_timestamps=[invalid_search.request.timestamp],
                )

    def _test_delete_sub_faulty(self):
        """Try to delete subscription in an incorrect way"""
        for sub_id in self._current_subscriptions.keys():

            del_missing_version = self._dss.delete_subscription(
                sub_id=sub_id, sub_version=""
            )
            self.record_query(del_missing_version)

            with self.check("Missing version prevents deletion", self._pid) as check:
                if del_missing_version.status_code != 400:
                    check.record_failed(
                        "Missing version did not prevent deletion",
                        details=f"Missing version did not prevent deletion, received status code {del_missing_version.status_code}",
                        query_timestamps=[del_missing_version.request.timestamp],
                    )

            del_wrong_version = self._dss.delete_subscription(
                sub_id=sub_id, sub_version="notacorrectversion"
            )
            self.record_query(del_wrong_version)

            with self.check("Incorrect version prevents deletion", self._pid) as check:
                if del_wrong_version.status_code != 409:
                    check.record_failed(
                        "Incorrect version did not prevent deletion",
                        details=f"Incorrect version did not prevent deletion, received status code {del_wrong_version.status_code}",
                        query_timestamps=[del_wrong_version.request.timestamp],
                    )

    def _test_delete_sub(self):
        """Delete the subscriptions in the correct way"""

        for sub_id, sub in self._current_subscriptions.items():
            deleted_sub = self._dss.delete_subscription(
                sub_id=sub_id, sub_version=sub.version
            )
            self.record_query(deleted_sub)
            with self.check("Delete subscription query succeeds", self._pid) as check:
                if not deleted_sub.success:
                    check.record_failed(
                        "Subscription deletion failed",
                        details=f"Subscription deletion failed with status code {deleted_sub.status_code}",
                        query_timestamps=[deleted_sub.request.timestamp],
                    )

            with self.check(
                "Delete subscription response is correct", self._pid
            ) as check:
                SubscriptionValidator(
                    check, self, self._pid, self._sub_params_by_sub_id[sub_id]
                ).validate_deleted_subscription(
                    sub_id,
                    deleted_sub,
                    self._current_subscriptions[sub_id].version,
                    False,
                )

        self._current_subscriptions = {}

    def _test_get_deleted_sub(self):
        """Try to retrieve the deleted subscription by its ID."""
        for sub_id in self._sub_params_by_sub_id.keys():
            not_found_sub = self._dss.get_subscription(sub_id)
            self.record_query(not_found_sub)
            with self.check(
                "Query by subscription ID should fail",
                self._pid,
            ) as check:
                if not_found_sub.status_code != 404:
                    check.record_failed(
                        "Query by subscription ID did not fail",
                        details=f"Query by subscription ID did not fail, received status code {not_found_sub.status_code}",
                        query_timestamps=[not_found_sub.request.timestamp],
                    )

    def _test_search_deleted_sub(self):
        """Try searching for the deleted subscription"""
        # Search should succeed
        subs_in_area = self._dss.query_subscriptions(self._planning_area_volume4d)
        self.record_query(subs_in_area)
        with self.check(
            "Search for all subscriptions in planning area query succeeds",
            self._pid,
        ) as check:
            if not subs_in_area.success:
                check.record_failed(
                    "Search for subscriptions in planning area failed",
                    details=f"Search for subscriptions in planning area failed with status code {subs_in_area.status_code}",
                    query_timestamps=[subs_in_area.request.timestamp],
                )

        with self.check(
            "Deleted subscription should not be present in search results",
            self._pid,
        ) as check:
            for sub_id in self._sub_params_by_sub_id.keys():
                if sub_id in subs_in_area.subscriptions:
                    check.record_failed(
                        "A deleted subscription is still present in search results",
                        details=f"The subscription {sub_id} was deleted, and thus not expected to be found in the search results."
                        f"Subscription IDs returned in search results: {subs_in_area.subscriptions.keys()}",
                        query_timestamps=[subs_in_area.request.timestamp],
                    )

    def _validate_subscription_and_notif_index(
        self,
        sub_id: str,
        sub_under_test: Subscription,
        creation_params: SubscriptionParams,
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
            self._pid,
        ) as check:
            if (
                sub_under_test.notification_index is not None
                and sub_under_test.notification_index < 0
            ):
                check.record_failed(
                    "Returned notification index is lower than 0",
                    details=f"Returned: {sub_under_test.notification_index} when 0 or more was expected"
                    f"Parameters used: {creation_params}",
                    query_timestamps=query_timestamps,
                )

    def _validate_subscription(
        self,
        sub_id: str,
        sub_under_test: Subscription,
        creation_params: SubscriptionParams,
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

        expect_start_time = creation_params.start_time
        expect_end_time = creation_params.end_time

        with self.check("Returned subscription has an ID", self._pid) as check:
            if not sub_under_test.id:
                check.record_failed(
                    "Returned subscription had no ID",
                    details="A subscription is expected to have an ID",
                    query_timestamps=query_timestamps,
                )

        with self.check("Returned subscription ID is correct", self._pid) as check:
            if sub_under_test.id != sub_id:
                check.record_failed(
                    "Returned subscription ID does not match provided one",
                    details=f"Provided: {sub_id}, Returned: {sub_under_test.id}",
                    query_timestamps=query_timestamps,
                )

        with self.check(
            "Returned subscription has an USS base URL", self._pid
        ) as check:
            if not sub_under_test.uss_base_url:
                check.record_failed(
                    "Returned subscription had no USS base URL",
                    details="A subscription is expected to have an USS base URL",
                    query_timestamps=query_timestamps,
                )

        with self.check(
            "Returned USS base URL has correct base URL", self._pid
        ) as check:
            if sub_under_test.uss_base_url != self._planning_area.get_base_url():
                check.record_failed(
                    "Returned USS Base URL does not match provided one",
                    details=f"Provided: {self._planning_area.get_base_url()}, Returned: {sub_under_test.uss_base_url}",
                    query_timestamps=query_timestamps,
                )

        with self.check("Returned subscription has a start time", self._pid) as check:
            if not sub_under_test.time_start:
                check.record_failed(
                    "Returned subscription had no start time",
                    details="A subscription is expected to have a start time",
                    query_timestamps=query_timestamps,
                )

        with self.check("Returned subscription has an end time", self._pid) as check:
            if not sub_under_test.time_end:
                check.record_failed(
                    "Returned subscription had no end time",
                    details="A subscription is expected to have an end time",
                    query_timestamps=query_timestamps,
                )

        # When expect_start_time has not been defined, there is no clear specification on
        # what the returned start time should be, so we only check it when we have requested one
        if expect_start_time is not None:
            with self.check("Returned start time is correct", self._pid) as check:
                if (
                    abs(
                        sub_under_test.time_start.value.datetime - expect_start_time
                    ).total_seconds()
                    > TIME_TOLERANCE_SEC
                ):
                    check.record_failed(
                        "Returned start time does not match provided one",
                        details=f"Provided: {expect_start_time}, Returned: {sub_under_test.time_start}",
                        query_timestamps=query_timestamps,
                    )

        # When expect_end_time has not been defined, there is no clear specification on
        # what the returned end time should be, so we only check it when we have requested one
        if expect_end_time is not None:
            with self.check("Returned end time is correct", self._pid) as check:
                if (
                    abs(
                        sub_under_test.time_end.value.datetime - expect_end_time
                    ).total_seconds()
                    > TIME_TOLERANCE_SEC
                ):
                    check.record_failed(
                        "Returned end time does not match provided one",
                        details=f"Provided: {expect_end_time}, Returned: {sub_under_test.time_end}",
                        query_timestamps=query_timestamps,
                    )

        with self.check("Returned subscription has a version", self._pid) as check:
            if not sub_under_test.version:
                check.record_failed(
                    "Returned subscription had no version",
                    details="A subscription is expected to have a version",
                    query_timestamps=query_timestamps,
                )

        # If the subscription was mutated, we compare the returned version with the previously stored one:
        if was_mutated:
            with self.check(
                "Mutated subscription version is updated",
                self._pid,
            ) as check:
                if (
                    sub_under_test.version
                    == self._current_subscriptions[sub_under_test.id].version
                ):
                    check.record_failed(
                        "Returned subscription version was not updated",
                        details=f"Returned: {sub_under_test.version}, Expected: {self._current_subscriptions[sub_under_test.id]}",
                        query_timestamps=query_timestamps,
                    )
        elif sub_id in self._current_subscriptions.keys():
            with self.check(
                "Non-mutated subscription keeps the same version",
                self._pid,
            ) as check:
                if (
                    sub_under_test.version
                    != self._current_subscriptions[sub_under_test.id].version
                ):
                    check.record_failed(
                        "Returned subscription version was updated",
                        details=f"Returned: {sub_under_test.version}, Expected: {self._current_subscriptions[sub_under_test.id]}.",
                        query_timestamps=query_timestamps,
                    )

        # Check implicit_subscription is false (in this scenario we created all subscriptions ourselves)
        with self.check(
            "Non-implicit subscription has implicit flag set to false",
            self._pid,
        ) as check:
            if sub_under_test.implicit_subscription:
                check.record_failed(
                    "Returned subscription has implicit_subscription set to true",
                    details="An explicitly created subscription is expected to have implicit_subscription set to false",
                    query_timestamps=query_timestamps,
                )

        with self.check(
            "Operational intents notification flag is as requested",
            self._pid,
        ) as check:
            if (
                sub_under_test.notify_for_operational_intents
                != creation_params.notify_for_op_intents
            ):
                check.record_failed(
                    "Returned subscription has notify_for_operational_intents set to a different value than requested",
                    details=f"Requested: {creation_params.notify_for_op_intents}, Returned: {sub_under_test.notify_for_operational_intents}",
                    query_timestamps=query_timestamps,
                )

        with self.check(
            "Constraints notification flag is as requested",
            self._pid,
        ) as check:
            if (
                sub_under_test.notify_for_constraints
                != creation_params.notify_for_constraints
            ):
                check.record_failed(
                    "Returned subscription has notify_for_constraints set to a different value than requested",
                    details=f"Requested: {creation_params.notify_for_constraints}, Returned: {sub_under_test.notify_for_constraints}",
                    query_timestamps=query_timestamps,
                )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_test_sub_ids_do_not_exist()
        self.end_cleanup()
