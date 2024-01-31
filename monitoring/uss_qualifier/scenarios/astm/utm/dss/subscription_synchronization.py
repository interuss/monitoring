from datetime import datetime, timedelta
from typing import List, Optional

import loguru
from uas_standards.astm.f3548.v21.api import Subscription, SubscriptionID
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
    DSSInstancesResource,
    DSSInstance,
)
from monitoring.uss_qualifier.resources.astm.f3548.v21.planning_area import (
    SubscriptionParams,
)
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.subscription_validator import (
    SubscriptionValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class SubscriptionSynchronization(TestScenario):
    """
    A scenario that checks if multiple DSS instances properly synchronize
    created, updated or deleted entities between them.

    Not in the scope of the first version of this:
     - access rights (making sure only the manager of the subscription can mutate it)
     - control of the area synchronization (by doing area searches against the secondaries)
     - mutation of a subscription on a secondary DSS when it was created on the primary
     - deletion of a subscription on a secondary DSS when it was created on the primary
    """

    SUB_TYPE = register_resource_type(379, "Subscription")

    _dss: DSSInstance

    _dss_read_instances: List[DSSInstance]

    # Base identifier for the subscriptions that will be created
    _sub_id: SubscriptionID

    # Base parameters used for subscription creation
    _sub_params: SubscriptionParams

    # Keep track of the current subscription state
    _current_subscription = Optional[Subscription]

    def __init__(
        self,
        dss: DSSInstanceResource,
        other_instances: DSSInstancesResource,
        id_generator: IDGeneratorResource,
        planning_area: PlanningAreaResource,
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
        self._planning_area = planning_area.specification

        # Build a ready-to-use 4D volume with no specified time for searching
        # the currently active subscriptions
        self._planning_area_volume4d = Volume4D(
            volume=self._planning_area.volume,
        )

        self._sub_params = self._planning_area.get_new_subscription_params(
            subscription_id=self._sub_id,
            # Set this slightly in the past: we will update the subscriptions
            # to a later value that still needs to be roughly 'now' without getting into the future
            start_time=datetime.now().astimezone() - timedelta(seconds=10),
            duration=timedelta(minutes=20),
            # This is a planning area without constraint processing
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )

    def run(self, context: ExecutionContext):

        # Check that we actually have at least one other DSS to test against:
        if not self._dss_read_instances:
            loguru.logger.warning(
                "Skipping EntitySynchronization test: no other DSS instances to test against"
            )
            return

        self.begin_test_scenario(context)
        self._setup_case()
        self.begin_test_case("Subscription Synchronization")

        self.begin_test_step("Create subscription validation")
        self._create_sub_with_params(self._sub_params)
        self.end_test_step()

        self.begin_test_step("Query newly created subscription")
        self._query_secondaries_and_compare(self._sub_params)
        self.end_test_step()

        self.begin_test_step("Mutate subscription")
        self._test_mutate_subscriptions_shift_time()
        self.end_test_step()

        self.begin_test_step("Query updated subscription")
        self._query_secondaries_and_compare(self._sub_params)
        self.end_test_step()

        self.begin_test_step("Delete subscription")
        self._test_delete_sub()
        self.end_test_step()

        self.begin_test_step("Query deleted subscription")
        self._test_get_deleted_sub()
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")
        # Multiple runs of the scenario seem to rely on the same instance of it:
        # thus we need to reset the state of the scenario before running it.
        self._current_subscription = None
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

    def _ensure_no_active_subs_exist(self):
        test_step_fragments.cleanup_active_subs(
            self,
            self._dss,
            self._planning_area_volume4d,
        )

    def _create_sub_with_params(self, creation_params: SubscriptionParams):

        # TODO migrate to the try/except pattern for queries
        newly_created = self._dss.upsert_subscription(
            **creation_params,
        )
        self.record_query(newly_created)

        with self.check(
            "Create subscription query succeeds", [self._primary_pid]
        ) as check:
            if not newly_created.success:
                loguru.logger.debug(f"Failed query: {newly_created.response.json}")
                check.record_failed(
                    "Subscription creation failed",
                    details=f"Subscription creation failed with status code {newly_created.status_code}",
                    query_timestamps=[newly_created.request.timestamp],
                )

        with self.check(
            "Create subscription response is correct", [self._primary_pid]
        ) as check:
            SubscriptionValidator(
                check,
                self,
                [self._primary_pid],
                creation_params,
            ).validate_created_subscription(creation_params.sub_id, newly_created)

        # Store the subscription
        self._current_subscription = newly_created.subscription

    def _query_secondaries_and_compare(self, expected_sub_params: SubscriptionParams):
        for secondary_dss in self._dss_read_instances:
            self._validate_sub_from_secondary(
                secondary_dss=secondary_dss,
                expected_sub_params=expected_sub_params,
                involved_participants=list(
                    {self._primary_pid, secondary_dss.participant_id}
                ),
            )

    def _validate_sub_from_secondary(
        self,
        secondary_dss: DSSInstance,
        expected_sub_params: SubscriptionParams,
        involved_participants: List[str],
    ):
        with self.check(
            "Subscription can be found at every DSS",
            involved_participants,
        ) as check:
            fetched_sub = secondary_dss.get_subscription(expected_sub_params.sub_id)
            self.record_query(fetched_sub)
            if fetched_sub.status_code != 200:
                check.record_failed(
                    "Get query for existing subscription failed",
                    details=f"Get query for a subscription expected to exist failed with status code {fetched_sub.status_code}",
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
            "Subscription returned by a secondary DSS is valid and correct",
            [secondary_dss.participant_id],
        ) as check:
            # Do a full validation of the subscription as a sanity check
            SubscriptionValidator(
                check,
                self,
                [secondary_dss.participant_id],
                expected_sub_params,
            ).validate_fetched_subscription(
                expected_sub_id=expected_sub_params.sub_id,
                fetched_sub=fetched_sub,
                expected_version=self._current_subscription.version,
                is_implicit=False,
            )

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
            [self._primary_pid],
        ) as check:
            if not creation_resp_under_test.subscription:
                check.record_failed(
                    "Response to subscription creation did not contain a subscription",
                    details="A subscription is expected to be returned in the response to a subscription creation request."
                    f"Parameters used: {creation_params}",
                    query_timestamps=[creation_resp_under_test.request.timestamp],
                )

        with self.check(
            "Mutate subscription response format conforms to spec", [self._primary_pid]
        ) as check:
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

    def _test_mutate_subscriptions_shift_time(self):
        """Mutate the subscription by adding 10 seconds to its start and end times"""

        op = self._sub_params
        sub = self._current_subscription
        new_params = SubscriptionParams(
            sub_id=self._sub_id,
            area_vertices=op.area_vertices,
            min_alt_m=op.min_alt_m,
            max_alt_m=op.max_alt_m,
            start_time=sub.time_start.value.datetime + timedelta(seconds=10),
            end_time=sub.time_end.value.datetime + timedelta(seconds=10),
            base_url=op.base_url,
            notify_for_op_intents=op.notify_for_op_intents,
            notify_for_constraints=op.notify_for_constraints,
        )
        mutated_sub_response = self._dss.upsert_subscription(
            version=sub.version,
            **new_params,
        )
        self.record_query(mutated_sub_response)
        with self.check("Subscription can be mutated", [self._primary_pid]) as check:
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

    def _test_delete_sub(self):
        deleted_sub = self._dss.delete_subscription(
            sub_id=self._sub_id, sub_version=self._current_subscription.version
        )
        self.record_query(deleted_sub)
        with self.check("Subscription can be deleted", [self._primary_pid]) as check:
            if deleted_sub.status_code != 200:
                check.record_failed(
                    "Subscription deletion failed",
                    details=f"Subscription deletion failed with status code {deleted_sub.status_code}",
                    query_timestamps=[deleted_sub.request.timestamp],
                )

        with self.check(
            "Delete subscription response format conforms to spec", [self._primary_pid]
        ) as check:
            SubscriptionValidator(
                check,
                self,
                [self._primary_pid],
                self._sub_params,
            ).validate_deleted_subscription(
                expected_sub_id=self._sub_id,
                deleted_subscription=deleted_sub,
                expected_version=self._current_subscription.version,
                is_implicit=False,
            )

        self._current_subscription = None

    def _test_get_deleted_sub(self):
        for secondary_dss in self._dss_read_instances:
            self._confirm_secondary_has_no_sub(secondary_dss)

    def _confirm_secondary_has_no_sub(self, secondary_dss: DSSInstance):
        fetched_sub = secondary_dss.get_subscription(self._sub_id)
        with self.check(
            "Secondary DSS should not return the deleted subscription",
            [secondary_dss.participant_id],
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
