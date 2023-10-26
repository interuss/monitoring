from typing import Optional

import arrow

from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss import utils
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario


class ISASubscriptionInteractions(GenericTestScenario):
    """Based on the test_subscription_isa_interactions.py from the legacy prober tool."""

    ISA_TYPE = register_resource_type(370, "ISA")

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        isa: ServiceAreaResource,
    ):
        super().__init__()
        self._dss = (
            dss.dss_instance
        )  # TODO: delete once _delete_isa_if_exists updated to use dss_wrapper
        self._dss_wrapper = DSSWrapper(self, dss.dss_instance)
        self._isa_id = id_generator.id_factory.make_id(
            ISASubscriptionInteractions.ISA_TYPE
        )
        # sub id is isa_id with last character replaced with '1'
        # (the generated isa_id ends with a few '0's)
        self._sub_id = self._isa_id[:-1] + "1"
        self._isa_version: Optional[str] = None
        self._isa = isa.specification

        now = arrow.utcnow().datetime
        self._isa_start_time = self._isa.shifted_time_start(now)
        self._isa_end_time = self._isa.shifted_time_end(now)
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]

    def run(self):
        self.begin_test_scenario()

        self._setup_case()

        self.begin_test_case("ISA Subscription Interactions")
        self.begin_test_step("ISA Subscription Interactions")

        self._check_subscription_behaviors()

        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()

    def _check_subscription_behaviors(self):
        """
        - Create an ISA.
        - Create a subscription, response should include the pre-existing ISA and have a notification_index of 0.
        - Modify the ISA, response should include the subscription with an incremented notification_index.
        - Delete the ISA, response should include the subscription with an incremented notification_index.
        - Delete the subscription.
        """

        # Create an ISA
        with self.check("Create an ISA", [self._dss.participant_id]) as check:
            created_isa = self._dss_wrapper.put_isa_expect_response_code(
                check=check,
                expected_error_codes={200},
                area_vertices=self._isa_area,
                alt_lo=self._isa.altitude_min,
                alt_hi=self._isa.altitude_max,
                start_time=self._isa_start_time,
                end_time=self._isa_end_time,
                uss_base_url=self._isa.base_url,
                isa_id=self._isa_id,
                isa_version=None,
            )

        # Create a subscription
        with self.check(
            "Create a subscription within the ISA footprint", [self._dss.participant_id]
        ) as check:
            created_subscription = self._dss_wrapper.put_sub(
                check=check,
                area_vertices=self._isa_area,
                alt_lo=self._isa.altitude_min,
                alt_hi=self._isa.altitude_max,
                start_time=self._isa_start_time,
                end_time=self._isa_end_time,
                uss_base_url=self._isa.base_url,
                sub_id=self._sub_id,
                sub_version=None,
            )

        # Check the subscription
        with self.check(
            "Subscription for the ISA's area mentions the ISA",
            [self._dss.participant_id],
        ) as check:
            if created_isa.dss_query.isa.id not in [
                isa.id for isa in created_subscription.isas
            ]:
                check.record_failed(
                    summary="Subscription response does not include the freshly created ISA",
                    severity=Severity.High,
                    participants=[self._dss.participant_id],
                    details=f"The subscription created for the area {self._isa_area} is expected to contain the ISA created for this same area. The returned subscription did not mention it.",
                    query_timestamps=[
                        created_isa.dss_query.query.request.timestamp,
                        created_subscription.query.request.timestamp,
                    ],
                )

        with self.check(
            "Newly created subscription has a notification_index of 0",
            [self._dss.participant_id],
        ) as check:
            if created_subscription.subscription.notification_index != 0:
                check.record_failed(
                    summary="Subscription notification_index is not 0",
                    severity=Severity.High,
                    participants=[self._dss.participant_id],
                    details=f"The subscription created for the area {self._isa_area} is expected to have a notification_index of 0. The returned subscription has a notification_index of {created_subscription.subscription.notification_index}.",
                    query_timestamps=[created_subscription.query.request.timestamp],
                )

        # Modify the ISA
        with self.check(
            "Mutate the ISA",
            [self._dss.participant_id],
        ) as check:
            mutated_isa = self._dss_wrapper.put_isa_expect_response_code(
                check=check,
                expected_error_codes={200},
                area_vertices=self._isa_area,
                alt_lo=self._isa.altitude_min,
                alt_hi=self._isa.altitude_max - 1,  # reduce max altitude by one meter
                start_time=self._isa_start_time,
                end_time=self._isa_end_time,
                uss_base_url=self._isa.base_url,
                isa_id=self._isa_id,
                isa_version=created_isa.dss_query.isa.version,
            )

        # Check that the subscription ID is returned in the response
        with self.check(
            "Response to the mutation of the ISA contains subscription ID",
            [self._dss.participant_id],
        ) as check:

            subs_to_mutated_isa = {}
            for returned_subscriber in mutated_isa.dss_query.subscribers:
                for sub_in_subscriber in returned_subscriber.raw.subscriptions:
                    subs_to_mutated_isa[
                        sub_in_subscriber.subscription_id
                    ] = sub_in_subscriber

            if created_subscription.subscription.id not in subs_to_mutated_isa.keys():
                check.record_failed(
                    summary="ISA mutation response does not contain expected subscription ID",
                    severity=Severity.High,
                    participants=[self._dss.participant_id],
                    details="Mutating an ISA to which a subscription was made, the DSS failed to return the subscription ID in the response.",
                    query_timestamps=[
                        created_isa.dss_query.query.request.timestamp,
                        created_subscription.query.request.timestamp,
                        mutated_isa.dss_query.query.request.timestamp,
                    ],
                )

        # Check that the subscription index has been incremented by least by 1
        sub_to_mutated_isa = subs_to_mutated_isa.get(
            created_subscription.subscription.id
        )
        if sub_to_mutated_isa is not None:
            with self.check(
                "Subscription to an ISA has its notification index incremented after mutation",
                [self._dss.participant_id],
            ) as check:
                if sub_to_mutated_isa.notification_index <= 0:
                    check.record_failed(
                        summary="Subscription notification_index has not been increased",
                        severity=Severity.High,
                        participants=[self._dss.participant_id],
                        details=f"The subscription created for the area {self._isa_area} is expected to have a notification_index of 1 or more. The returned subscription has a notification_index of {subs_to_mutated_isa[created_subscription.subscription.id].notification_index}.",
                        query_timestamps=[created_subscription.query.request.timestamp],
                    )

        # Delete the ISA
        with self.check(
            "Delete the ISA",
            [self._dss.participant_id],
        ) as check:
            deleted_isa = self._dss_wrapper.del_isa_expect_response_code(
                main_check=check,
                expected_error_codes={200},
                isa_id=mutated_isa.dss_query.isa.id,
                isa_version=mutated_isa.dss_query.isa.version,
            )

        # Check response to deletion of ISA
        with self.check(
            "Response to the deletion of the ISA contains subscription ID",
            [self._dss.participant_id],
        ) as check:

            subs_to_deleted_isa = {}
            for returned_subscriber in deleted_isa.dss_query.subscribers:
                for sub_in_subscriber in returned_subscriber.raw.subscriptions:
                    subs_to_deleted_isa[
                        sub_in_subscriber.subscription_id
                    ] = sub_in_subscriber

            if created_subscription.subscription.id not in subs_to_deleted_isa:
                check.record_failed(
                    summary="ISA deletion response does not contain expected subscription ID",
                    severity=Severity.High,
                    participants=[self._dss.participant_id],
                    details="Deleting an ISA to which a subscription was made, the DSS failed to return the subscription ID in the response.",
                    query_timestamps=[
                        created_isa.dss_query.query.request.timestamp,
                        created_subscription.query.request.timestamp,
                        deleted_isa.dss_query.query.request.timestamp,
                    ],
                )

        for subscriber_url, notification in deleted_isa.notifications.items():
            # For checking the notifications, we ignore the request we made for the subscription that we created.
            if self._isa.base_url not in subscriber_url:
                with self.check("Notified subscriber", [subscriber_url]) as check:
                    # TODO: Find a better way to identify a subscriber who couldn't be notified:
                    #  as-is the subscriber url causes the test-suite to crash when it writes its report
                    if not notification.success:
                        check.record_failed(
                            "Could not notify ISA subscriber",
                            Severity.Medium,
                            f"Attempting to notify subscriber for ISA {self._isa_id} at {subscriber_url} resulted in {notification.status_code}",
                            query_timestamps=[notification.query.request.timestamp],
                        )

        subs_after_deletion = subs_to_deleted_isa.get(
            created_subscription.subscription.id
        )
        if subs_after_deletion is not None:
            with self.check(
                "Subscription to an ISA has its notification index incremented after deletion",
                [self._dss.participant_id],
            ) as check:
                if (
                    subs_after_deletion.notification_index
                    <= sub_to_mutated_isa.notification_index
                ):
                    check.record_failed(
                        summary="Subscription notification_index has not been incremented",
                        severity=Severity.High,
                        participants=[self._dss.participant_id],
                        details=f"The subscription created for the area {self._isa_area} is expected to have its notification increased after the subscription was deleted."
                        f"The returned subscription has a notification_index of {subs_after_deletion.notification_index}, whilte the previous notification_index for that subscription was {sub_to_mutated_isa.notification_index}",
                        query_timestamps=[created_subscription.query.request.timestamp],
                    )

        # Delete the subscription
        with self.check(
            "Successful subscription deletion",
            [self._dss.participant_id],
        ) as check:
            self._dss_wrapper.del_sub(
                check=check,
                sub_id=self._sub_id,
                sub_version=created_subscription.subscription.version,
            )

    def _setup_case(self):
        self.begin_test_case("Setup")

        def _ensure_clean_workspace_step():
            self.begin_test_step("Ensure clean workspace")

            self._delete_isa_if_exists()
            self._clean_any_sub()

            self.end_test_step()

        _ensure_clean_workspace_step()

        self.end_test_case()

    def _delete_isa_if_exists(self):
        utils.delete_isa_if_exists(
            self,
            isa_id=self._isa_id,
            rid_version=self._dss.rid_version,
            session=self._dss.client,
            participant_id=self._dss_wrapper.participant_id,
        )

    def _clean_any_sub(self):
        utils.delete_any_subscription(self, self._dss_wrapper, self._isa.footprint)

    def cleanup(self):
        self.begin_cleanup()

        self._delete_isa_if_exists()
        self._clean_any_sub()

        self.end_cleanup()
