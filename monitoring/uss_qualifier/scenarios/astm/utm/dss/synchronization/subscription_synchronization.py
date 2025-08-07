from datetime import datetime, timedelta

import loguru
from uas_standards.astm.f3548.v21.api import Subscription, SubscriptionID
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib import geo, schema_validation
from monitoring.monitorlib.geo import Volume3D
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.monitorlib.schema_validation import F3548_21
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DSSInstanceResource,
    DSSInstancesResource,
)
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.planning_area import SubscriptionParams
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.sub.crud import (
    sub_create_query,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.validators import (
    fail_with_schema_errors,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.validators.subscription_validator import (
    SubscriptionValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class SubscriptionSynchronization(TestScenario):
    """
    A scenario that checks if multiple DSS instances properly synchronize
    created, updated or deleted entities between them.

    Not in the scope of the current version:
     - access rights (making sure only the manager of the subscription can mutate it)

    """

    SUB_TYPE = register_resource_type(379, "Subscription")
    ACL_SUB_TYPE = register_resource_type(
        381, "Subscription with different credentials"
    )

    _dss: DSSInstance

    # Separate DSS client for testing manager synchronization
    _dss_separate_creds: DSSInstance | None

    _dss_read_instances: list[DSSInstance]

    # Base identifier for the subscriptions that will be created
    _sub_id: SubscriptionID

    # Extra sub IDs for testing only deletions
    _ids_for_deletion: list[SubscriptionID]

    # Extra sub id for testing manager sync
    _acl_sub_id: SubscriptionID
    # The extra subscription for testing manager sync
    _current_acl_sub: Subscription

    # Base parameters used for subscription creation
    _sub_params: SubscriptionParams

    # Keep track of the current subscription state
    _current_subscription = Subscription | None

    # For the secondary deletion test
    _subs_for_deletion: dict[SubscriptionID, Subscription]

    def __init__(
        self,
        dss: DSSInstanceResource,
        other_instances: DSSInstancesResource,
        id_generator: IDGeneratorResource,
        planning_area: PlanningAreaResource,
        second_utm_auth: AuthAdapterResource | None = None,
    ):
        """
        Args:
            dss: dss to test
            id_generator: will let us generate specific identifiers
            planning_area: An Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.
        """
        super().__init__()
        scopes_primary = {
            Scope.StrategicCoordination: "create and delete subscriptions"
        }
        scopes_read = {Scope.StrategicCoordination: "read subscriptions"}

        self._dss = dss.get_instance(scopes_primary)
        self._primary_pid = self._dss.participant_id

        self._dss_read_instances = [
            sec_dss.get_instance(scopes_read)
            for sec_dss in other_instances.dss_instances
        ]

        self._sub_id = id_generator.id_factory.make_id(self.SUB_TYPE)

        # For every secondary DSS, have an extra sub ID for testing deletion at each DSS
        # TODO confirm that we can have as many SCD subscriptions as we want (RID limits them to 10 per area)
        # TODO IDGenerators may encode the subject/identity of the participant being tested into the ID,
        #  therefore we may want to consider having a separate generator per DSS instance,
        #  or at least one per participant
        self._ids_for_deletion = [
            f"{self._sub_id[:-3]}{i:03d}"
            for i in range(1, len(self._dss_read_instances) + 1)
        ]

        self._acl_sub_id = id_generator.id_factory.make_id(self.ACL_SUB_TYPE)
        self._planning_area = planning_area.specification

        # Build a ready-to-use 4D volume with no specified time for searching
        # the currently active subscriptions
        self._planning_area_volume4d = Volume4D(
            volume=self._planning_area.volume,
        )

        # Get a list of vertices enclosing the area
        enclosing_area = geo.get_latlngrect_vertices(
            geo.make_latlng_rect(self._planning_area_volume4d.volume)
        )

        self._enclosing_sub_area_volume4d = Volume4D(
            volume=Volume3D(
                outline_polygon=geo.Polygon.from_latlng_coords(enclosing_area)
            )
        )

        # Get a list of vertices outside the subscription's area
        outside_area = geo.generate_area_in_vicinity(enclosing_area, 2)

        self._outside_sub_area_volume4d = Volume4D(
            volume=Volume3D(
                outline_polygon=geo.Polygon.from_latlng_coords(outside_area)
            )
        )

        if second_utm_auth is not None:
            # Build a second DSSWrapper identical to the first but with the other auth adapter
            self._dss_separate_creds = self._dss.with_different_auth(
                second_utm_auth, scopes_primary
            )
        else:
            self._dss_separate_creds = None

        self._current_subscription = None
        self._subs_for_deletion = {}
        self._subs_for_deletion_params = {}

    def run(self, context: ExecutionContext):
        self._sub_params = self._planning_area.get_new_subscription_params(
            subscription_id=self._sub_id,
            # Set this slightly in the past: we will update the subscriptions
            # to a later value that still needs to be roughly 'now' without getting into the future
            start_time=datetime.now().astimezone() - timedelta(seconds=10),
            duration=timedelta(minutes=45),
            # This is a planning area without constraint processing
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )

        # Check that we actually have at least one other DSS to test against:
        if not self._dss_read_instances:
            loguru.logger.warning(
                "Skipping EntitySynchronization test: no other DSS instances to test against"
            )
            return

        self.begin_test_scenario(context)
        self._step_setup_case()
        self.begin_test_case("Subscription Synchronization")

        self.begin_test_step("Create subscription validation")
        self._step_create_subscriptions()
        self.end_test_step()

        self.begin_test_step("Query newly created subscription")
        self._step_query_secondaries_and_compare(self._sub_params)
        self.end_test_step()

        self.begin_test_step("Mutate subscription broadcast")
        self._step_mutate_subscriptions_broadcast_shift_time()
        self.end_test_step()

        self.begin_test_step("Query updated subscription")
        self._step_query_secondaries_and_compare(self._sub_params)
        self.end_test_step()

        if self._dss_separate_creds:
            self.begin_test_step("Create subscription with different credentials")
            self._step_create_sub_separate_creds()
            self.end_test_step()
            self.begin_test_step("Verify manager synchronization")
            self._step_test_delete_sub_with_separate_creds()
            self.end_test_step()
        else:
            self.record_note(
                "manager_check",
                "Skipping manager synchronization check: no extra credentials provided",
            )

        self._repeat_steps_mutate_subscriptions_secondaries_shift_time()

        self.begin_test_step("Delete subscription on primary")
        self._step_delete_sub()
        self.end_test_step()

        self.begin_test_step("Query deleted subscription")
        self._step_get_deleted_sub()
        self.end_test_step()

        self.begin_test_step("Delete subscriptions on secondaries")
        self._step_delete_subscriptions_on_secondaries()
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _step_setup_case(self):
        self.begin_test_case("Setup")
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
        test_step_fragments.cleanup_sub(self, self._dss, self._sub_id)
        for sub_id in self._ids_for_deletion:
            test_step_fragments.cleanup_sub(self, self._dss, sub_id)
        if self._dss_separate_creds:
            test_step_fragments.cleanup_sub(
                self, self._dss_separate_creds, self._acl_sub_id
            )

    def _ensure_no_active_subs_exist(self):
        test_step_fragments.cleanup_active_subs(
            self,
            self._dss,
            self._planning_area_volume4d,
        )

    def _step_create_subscriptions(self):
        # Create the 'main' test subscription:
        self._current_subscription = self._create_sub_with_params(self._sub_params)

        # Create the extra subscriptions for testing deletion on secondaries at the end of the scenario
        for sub_id in self._ids_for_deletion:
            params = self._sub_params.copy()
            params.sub_id = sub_id
            extra_sub = self._create_sub_with_params(params)
            self._subs_for_deletion[sub_id] = extra_sub
            self._subs_for_deletion_params[sub_id] = params

    def _create_sub_with_params(
        self, creation_params: SubscriptionParams
    ) -> Subscription:
        _, _, newly_created = sub_create_query(self, self._dss, creation_params)

        with self.check(
            "Create subscription response content is correct", [self._primary_pid]
        ) as check:
            SubscriptionValidator(
                check,
                self,
                [self._primary_pid],
                creation_params,
            ).validate_created_subscription(creation_params.sub_id, newly_created)

        return newly_created.subscription

    def _step_query_secondaries_and_compare(
        self, expected_sub_params: SubscriptionParams
    ):
        for secondary_dss in self._dss_read_instances:
            self._validate_get_sub_from_secondary(
                secondary_dss=secondary_dss,
                expected_sub_params=expected_sub_params,
                involved_participants=list(
                    {self._primary_pid, secondary_dss.participant_id}
                ),
            )
            self._validate_sub_area_from_secondary(
                secondary_dss=secondary_dss,
                expected_sub_id=expected_sub_params.sub_id,
                involved_participants=list(
                    {self._primary_pid, secondary_dss.participant_id}
                ),
            )

    def _validate_sub_area_from_secondary(
        self,
        secondary_dss: DSSInstance,
        expected_sub_id: str,
        involved_participants: list[str],
    ):
        """Checks that the secondary DSS is also aware of the proper subscription's area:
        - searching for the subscription's area should yield the subscription
        - searching outside the subscription's area should not yield the subscription"""

        # Query the subscriptions inside the enclosing area
        sub_included = secondary_dss.query_subscriptions(
            self._enclosing_sub_area_volume4d.to_f3548v21()
        )

        with self.check(
            "Successful subscription search query", secondary_dss.participant_id
        ) as check:
            if sub_included.status_code != 200:
                check.record_failed(
                    "Subscription search query failed",
                    details=f"Subscription search query failed with status code {sub_included.status_code}",
                    query_timestamps=[sub_included.request.timestamp],
                )

        with self.check(
            "Secondary DSS returns the subscription in searches for area that contains it",
            involved_participants,
        ) as check:
            if expected_sub_id not in sub_included.subscriptions:
                check.record_failed(
                    "Secondary DSS did not return the subscription",
                    details=f"Secondary DSS did not return the subscription {expected_sub_id} "
                    f"although the search volume covered the subscription's area",
                    query_timestamps=[sub_included.request.timestamp],
                )

        sub_not_included = secondary_dss.query_subscriptions(
            self._outside_sub_area_volume4d.to_f3548v21()
        )

        with self.check(
            "Successful subscription search query", secondary_dss.participant_id
        ) as check:
            if sub_not_included.status_code != 200:
                check.record_failed(
                    summary="Subscription search query failed",
                    details=f"Subscription search query failed with status code {sub_included.status_code}",
                    query_timestamps=[sub_included.request.timestamp],
                )

        with self.check(
            "Secondary DSS does not return the subscription in searches not encompassing the general area of the subscription",
            involved_participants,
        ) as check:
            if expected_sub_id in sub_not_included.subscriptions:
                check.record_failed(
                    summary="Secondary DSS returned the subscription",
                    details=f"Secondary DSS returned the subscription {expected_sub_id} "
                    f"although the search volume did not cover the subscription's general area",
                    query_timestamps=[sub_not_included.request.timestamp],
                )

    def _validate_get_sub_from_secondary(
        self,
        secondary_dss: DSSInstance,
        expected_sub_params: SubscriptionParams,
        involved_participants: list[str],
    ):
        """Fetches the subscription from the secondary DSS and validates it."""
        with self.check(
            "Get Subscription by ID",
            secondary_dss.participant_id,
        ) as check:
            fetched_sub = secondary_dss.get_subscription(expected_sub_params.sub_id)
            self.record_query(fetched_sub)
            # At this point we just check that the request itself returned successfully.
            if fetched_sub.error_message is not None:
                check.record_failed(
                    "Get query for existing subscription failed",
                    details=f"Get query for a subscription expected to exist failed with status code {fetched_sub.status_code}, error: {fetched_sub.error_message}",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

        with self.check(
            "Subscription can be found at every DSS", involved_participants
        ) as check:
            if fetched_sub.status_code != 200:
                check.record_failed(
                    "Subscription was not found at every DSS",
                    details=f"Get query for a subscription expected to exist failed with status code {fetched_sub.status_code}.",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

        sub = fetched_sub.subscription
        with self.check(
            "Propagated subscription contains the correct USS base URL",
            involved_participants,
        ) as check:
            base_url = (
                sub.uss_base_url if sub.has_field_with_value("uss_base_url") else None
            )
            if base_url != expected_sub_params.base_url:
                check.record_failed(
                    "Propagated subscription has an incorrect USS base URL",
                    details=f"Expected: {expected_sub_params.base_url}, Received: {base_url}",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

        with self.check(
            "Propagated subscription contains the correct start time",
            involved_participants,
        ) as check:
            start_time = (
                sub.time_start.value.datetime
                if sub.has_field_with_value("time_start")
                else None
            )
            if start_time != expected_sub_params.start_time:
                check.record_failed(
                    "Propagated subscription has an incorrect start time",
                    details=f"Expected: {expected_sub_params.start_time}, Received: {start_time}",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

        with self.check(
            "Propagated subscription contains the correct end time",
            involved_participants,
        ) as check:
            end_time = (
                sub.time_end.value.datetime
                if sub.has_field_with_value("time_end")
                else None
            )
            if end_time != expected_sub_params.end_time:
                check.record_failed(
                    "Propagated subscription has an incorrect end time",
                    details=f"Expected: {expected_sub_params.end_time}, Received: {end_time}",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

        with self.check(
            "Propagated subscription contains the correct version",
            involved_participants,
        ) as check:
            version = sub.version if sub.has_field_with_value("version") else None
            if version != self._current_subscription.version:
                check.record_failed(
                    "Propagated subscription has an incorrect version",
                    details=f"Expected: {self._current_subscription.version}, Received: {version}",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

        with self.check(
            "Propagated subscription contains the correct notification flags",
            involved_participants,
        ) as check:
            notify_for_op_intents = (
                sub.notify_for_operational_intents
                if sub.has_field_with_value("notify_for_operational_intents")
                else None
            )
            notify_for_constraints = (
                sub.notify_for_constraints
                if sub.has_field_with_value("notify_for_constraints")
                else None
            )
            if notify_for_op_intents != expected_sub_params.notify_for_op_intents:
                check.record_failed(
                    "Propagated subscription has unexpected notify_for_op_intents flag",
                    details=f"Expected: {expected_sub_params.notify_for_op_intents}, Received: {notify_for_op_intents}",
                    query_timestamps=[fetched_sub.request.timestamp],
                )
            if notify_for_constraints != expected_sub_params.notify_for_constraints:
                check.record_failed(
                    "Propagated subscription has unexpected notify_for_constraints flag",
                    details=f"Expected: {expected_sub_params.notify_for_constraints}, Received: {notify_for_constraints}",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

        with self.check(
            "Propagated subscription contains the correct implicit flag",
            involved_participants,
        ) as check:
            is_implicit = (
                sub.implicit_subscription
                if sub.has_field_with_value("implicit_subscription")
                else None
            )
            # We created the subscription directly: it should not have the implicit flag
            if is_implicit:
                check.record_failed(
                    "Propagated subscription has an incorrect implicit flag",
                    details=f"Expected: {expected_sub_params.implicit_subscription}, Received: {is_implicit}",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

        with self.check(
            "Propagated subscription contains expected notification count",
            involved_participants,
        ) as check:
            notif_index = (
                sub.notification_index
                if sub.has_field_with_value("notification_index")
                else None
            )
            # Technically a notification may already have caused the index to be incremented, so we can't
            # strictly expect the retrieved one to be the same then at time of creation.
            # However, it should at least be the same.
            if (
                notif_index is None
                or notif_index < self._current_subscription.notification_index
            ):
                check.record_failed(
                    "Propagated subscription has an unexpected notification index",
                    details=f"Expected: 0 or more, Received: {notif_index}",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

        with self.check(
            "Get subscription response content is correct",
            involved_participants,
        ) as check:
            # The above checks validate synchronization requirements. The check below validates the correctness requirements
            # (The logic is similar, but it covers different requirements in the standard).
            SubscriptionValidator(
                check,
                self,
                involved_participants,
                expected_sub_params,
            ).validate_fetched_subscription(
                expected_sub_id=expected_sub_params.sub_id,
                fetched_sub=fetched_sub,
                expected_version=self._current_subscription.version,
                is_implicit=False,
                validate_schema=False,  # schema validated only for secondary DSS participant in check below
            )

        # Finally, validate the response schema
        with self.check(
            "Get subscription response format conforms to spec",
            secondary_dss.participant_id,
        ) as check:
            errors = schema_validation.validate(
                F3548_21.OpenAPIPath,
                F3548_21.GetSubscriptionResponse,
                fetched_sub.response.json,
            )
            if errors:
                fail_with_schema_errors(check, errors, fetched_sub.request.timestamp)

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
            "Mutate subscription response content is correct"
            if was_mutated
            else "Create subscription response content is correct"
        )

        with self.check(check_name, [self._primary_pid]) as check:
            if not creation_resp_under_test.subscription:
                check.record_failed(
                    "Response to subscription creation did not contain a subscription",
                    details=f"A subscription is expected to be returned in the response. "
                    f"Parameters used: {creation_params}",
                    query_timestamps=[creation_resp_under_test.request.timestamp],
                )
            SubscriptionValidator(
                check,
                self,
                [self._primary_pid],
                creation_params,
            ).validate_mutated_subscription(
                expected_sub_id=sub_id,
                mutated_sub=creation_resp_under_test,
                previous_version=self._current_subscription.version,
                is_implicit=False,
            )

    def _mutate_subscription_with_dss(
        self,
        dss_instance: DSSInstance,
        new_params: SubscriptionParams,
        is_primary: bool,
    ):
        """
        Mutate the subscription on the given DSS instance using the given parameters.
        Also updates the internal state of the scenario to reflect the new subscription.
        """
        check = (
            "Subscription can be mutated"
            if is_primary
            else "Subscription can be mutated on secondary DSS"
        )
        with self.check(check, [self._primary_pid]) as check:
            mutated_sub_response = dss_instance.upsert_subscription(
                version=self._current_subscription.version,
                **new_params,
            )
            self.record_query(mutated_sub_response)
            if mutated_sub_response.status_code != 200:
                check.record_failed(
                    "Subscription mutation failed",
                    details=f"Subscription mutation failed with status code {mutated_sub_response.status_code}",
                    query_timestamps=[mutated_sub_response.request.timestamp],
                )

        # Check that what we get back is valid and corresponds to what we want to create
        self._compare_upsert_resp_with_params(
            self._sub_id, mutated_sub_response, new_params, was_mutated=True
        )
        # Store the subscription
        self._current_subscription = mutated_sub_response.subscription
        # Update the parameters we used for that subscription
        self._sub_params = new_params

    def _step_create_sub_separate_creds(self):
        """Create a subscription on the main DSS with the separate credentials"""
        params = self._sub_params.copy()
        params.sub_id = self._acl_sub_id

        _, _, acl_sub = sub_create_query(self, self._dss_separate_creds, params)
        self._current_acl_sub = acl_sub.subscription

    def _step_test_delete_sub_with_separate_creds(self):
        """Check we can't delete the subscription created with separate credentials with the main credentials.
        This is to confirm that the manager of the subscription is properly synced.
        Note that if the separate credentials are for the same subject as the main one, the checks are skipped.
        """

        if not self._credentials_are_different():
            self.record_note(
                "manager_check",
                "Skipping manager synchronization check: "
                "separate credentials have the same subscriber as the main ones.",
            )
            return

        # For each secondary dss, try to delete the subscription using the main credentials:
        for secondary_dss in self._dss_read_instances:
            deleted_sub = secondary_dss.delete_subscription(
                sub_id=self._acl_sub_id, sub_version=self._current_acl_sub.version
            )
            self.record_query(deleted_sub)
            with self.check(
                "Subscription deletion with different non-managing credentials on secondary DSS fails",
                [secondary_dss.participant_id],
            ) as check:
                if deleted_sub.status_code != 403:
                    check.record_failed(
                        "Subscription deletion with main credentials did not fail",
                        details=f"Subscription deletion with main credentials did not fail with the expected "
                        f"status code of 403; instead returned {deleted_sub.status_code}",
                        query_timestamps=[deleted_sub.request.timestamp],
                    )

    def _credentials_are_different(self):
        """
        Checks the auth adapters for the subscription (jwt 'sub' field) they used and returns False if they are the same.
        Note that both adapters need to have been used at least once before this check can be performed,
        otherwise they have no token available.
        """
        return (
            self._dss_separate_creds.client.auth_adapter.get_sub()
            != self._dss.client.auth_adapter.get_sub()
        )

    def _step_mutate_subscriptions_broadcast_shift_time(self):
        """Mutate the subscription on the primary DSS by adding 10 seconds to its start and end times"""

        sp = self._sub_params
        new_params = sp.shift_time(timedelta(seconds=10))
        self._mutate_subscription_with_dss(self._dss, new_params, is_primary=True)

    def _repeat_steps_mutate_subscriptions_secondaries_shift_time(self):
        """Mutate the subscription on every secondary DSS by adding 10 seconds to its start and end times,
        then checking on every DSS that the response is valid and corresponds to the expected parameters.
        """

        for secondary_dss in self._dss_read_instances:
            # Mutate the subscription on the secondary DSS
            self.begin_test_step("Mutate subscription on secondaries")
            self._mutate_subscription_with_dss(
                secondary_dss,
                self._sub_params.shift_time(timedelta(seconds=10)),
                is_primary=False,
            )
            self.end_test_step()
            self.begin_test_step("Verify mutation on all secondaries")
            # Check that the mutation was propagated to every DSS:
            self._step_query_secondaries_and_compare(self._sub_params)
            self.end_test_step()

    def _delete_sub_from_dss(
        self,
        dss_instance: DSSInstance,
        sub_id: str,
        version: str,
        expected_params: SubscriptionParams,
    ) -> bool:
        """
        Delete the subscription on the given DSS instance using the given parameters.
        Returns True if the subscription was successfully deleted, False otherwise.
        """
        with self.check(
            "Subscription can be deleted", [dss_instance.participant_id]
        ) as check:
            deleted_sub = dss_instance.delete_subscription(sub_id, version)
            self.record_query(deleted_sub)
            if deleted_sub.status_code != 200:
                check.record_failed(
                    "Subscription deletion failed",
                    details=f"Subscription deletion failed with status code {deleted_sub.status_code}",
                    query_timestamps=[deleted_sub.request.timestamp],
                )
                return False

        with self.check(
            "Delete subscription response content is correct",
            [dss_instance.participant_id],
        ) as check:
            SubscriptionValidator(
                check,
                self,
                [dss_instance.participant_id],
                expected_params,
            ).validate_deleted_subscription(
                expected_sub_id=sub_id,
                deleted_subscription=deleted_sub,
                expected_version=version,
                is_implicit=False,
            )

        return True

    def _step_delete_sub(self):
        if self._delete_sub_from_dss(
            self._dss,
            self._sub_id,
            self._current_subscription.version,
            self._sub_params,
        ):
            self._current_subscription = None

    def _step_delete_subscriptions_on_secondaries(self):
        # Pair a sub ID to delete together with a secondary DSS
        for sub_id, secondary_dss in zip(
            self._ids_for_deletion, self._dss_read_instances
        ):
            # Delete the subscription on the secondary DSS
            if not self._delete_sub_from_dss(
                secondary_dss,
                sub_id,
                self._subs_for_deletion[sub_id].version,
                self._subs_for_deletion_params[sub_id],
            ):
                # If the deletion failed but the scenario has not terminated, we end this step here.
                return
            # Check that the primary knows about the deletion:
            self._confirm_dss_has_no_sub(
                self._dss, sub_id, secondary_dss.participant_id
            )
            # Check that the deletion was propagated to every DSS:
            self._confirm_no_secondary_has_sub(sub_id, secondary_dss.participant_id)

    def _step_get_deleted_sub(self):
        self._confirm_no_secondary_has_sub(self._sub_id, self._dss.participant_id)

    def _confirm_no_secondary_has_sub(
        self, sub_id: str, deleted_on_participant_id: str
    ):
        """Confirm that no secondary DSS has the subscription.
        deleted_on_participant_id specifies the participant_id of the DSS where the subscription was deleted.
        """
        for secondary_dss in self._dss_read_instances:
            self._confirm_dss_has_no_sub(
                secondary_dss, sub_id, deleted_on_participant_id
            )

    def _confirm_dss_has_no_sub(
        self,
        dss_instance: DSSInstance,
        sub_id: str,
        other_participant_id: str | None,
    ):
        """Confirm that a DSS has no subscription.
        other_participant_id may be specified if a failed check may be caused by it."""
        participants = [dss_instance.participant_id]
        if other_participant_id:
            participants.append(other_participant_id)
        fetched_sub = dss_instance.get_subscription(sub_id)
        with self.check(
            "DSS should not return the deleted subscription",
            participants,
        ) as check:
            if fetched_sub.status_code != 404:
                check.record_failed(
                    "Get query for deleted subscription did not return 404",
                    details=f"Get query for a deleted subscription returned status code {fetched_sub.status_code}",
                    query_timestamps=[fetched_sub.request.timestamp],
                )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_test_sub_ids_do_not_exist()
        self.end_cleanup()
