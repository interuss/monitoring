import datetime
import ipaddress
import socket
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from urllib.parse import urlparse

import s2sphere

from monitoring.monitorlib.delay import sleep
from monitoring.monitorlib.fetch.rid import ISA
from monitoring.monitorlib.geo import get_latlngrect_vertices, make_latlng_rect
from monitoring.uss_qualifier.resources import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3411.dss import (
    DSSInstanceResource,
    DSSInstancesResource,
)
from monitoring.uss_qualifier.resources.dev.test_exclusions import (
    TestExclusionsResource,
)
from monitoring.uss_qualifier.resources.planning_area import PlanningAreaSpecification
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

SHORT_WAIT_SEC = 5

DEFAULT_LOWER_ALT_M = 20
DEFAULT_UPPER_ALT_M = 400


class EntityType(str, Enum):
    ISA = "ISA"
    Sub = "Sub"


@dataclass
class TestEntity(object):
    type: EntityType
    uuid: str
    version: Optional[str] = None


class DSSInteroperability(GenericTestScenario):
    """
    TODO additional improvements/extensions:
     - cell ID synchronization checks can be improved further by search outside of the
       subscription's footprint on the secondary DSS and confirming it is not returned
    """

    _dss_primary: DSSWrapper
    _dss_others: List[DSSWrapper]
    _allow_private_addresses: bool = False
    _context: Dict[str, TestEntity]
    _area_vertices: List[s2sphere.LatLng]
    _planning_area: PlanningAreaSpecification

    def __init__(
        self,
        primary_dss_instance: DSSInstanceResource,
        all_dss_instances: DSSInstancesResource,
        planning_area: PlanningAreaResource,
        test_exclusions: Optional[TestExclusionsResource] = None,
    ):
        super().__init__()
        self._dss_primary = DSSWrapper(self, primary_dss_instance.dss_instance)
        self._dss_others = [
            DSSWrapper(self, dss)
            for dss in all_dss_instances.dss_instances
            if not dss.is_same_as(primary_dss_instance.dss_instance)
        ]

        self._planning_area = planning_area.specification
        self._area_vertices = get_latlngrect_vertices(
            make_latlng_rect(self._planning_area.volume)
        )
        if test_exclusions is not None:
            self._allow_private_addresses = test_exclusions.allow_private_addresses

        self._context: Dict[str, TestEntity] = {}

    # TODO migrate to ID generator?
    def _new_isa(self, name: str) -> TestEntity:
        self._context[name] = TestEntity(EntityType.ISA, str(uuid.uuid4()))
        return self._context[name]

    # TODO migrate to ID generator?
    def _new_sub(self, name: str) -> TestEntity:
        self._context[name] = TestEntity(EntityType.Sub, str(uuid.uuid4()))
        return self._context[name]

    def _get_entities_by_prefix(self, prefix: str) -> Dict[str, TestEntity]:
        all_entities = dict()
        for name, entity in self._context.items():
            if name.startswith(prefix):
                all_entities[entity.uuid] = entity
        return all_entities

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Prerequisites")

        self.begin_test_step("Test environment requirements")
        self._test_env_reqs()
        self.end_test_step()

        self.end_test_case()

        if self._dss_others:
            self.begin_test_case("Interoperability sequence")

            for i in range(1, 18):
                self.begin_test_step(f"S{i}")
                step = getattr(self, f"step{i}")
                step()
                self.end_test_step()

            self.end_test_case()

        self.end_test_scenario()

    def _test_env_reqs(self):
        for dss in [self._dss_primary] + self._dss_others:
            with self.check(
                "DSS instance is publicly addressable", [dss.participant_id]
            ) as check:
                parsed_url = urlparse(dss.base_url)
                ip_addr = socket.gethostbyname(parsed_url.hostname)

                if ipaddress.ip_address(ip_addr).is_private:
                    if self._allow_private_addresses:
                        check.skip()
                    else:
                        check.record_failed(
                            summary=f"DSS host {parsed_url.netloc} is not publicly addressable",
                            details=f"DSS (URL: {dss.base_url}, netloc: {parsed_url.netloc}, resolved IP: {ip_addr}) is not publicly addressable",
                        )

            with self.check("DSS instance is reachable", [dss.participant_id]) as check:
                # dummy search query
                dss.search_subs(check, self._area_vertices)

    def step1(self):
        """Create ISA in Primary DSS with 10 min TTL."""

        with self.check(
            "ISA[P] created with proper response", [self._dss_primary.participant_id]
        ) as check:
            isa_1 = self._new_isa("isa_1")

            mutated_isa = self._dss_primary.put_isa(
                check,
                isa_id=isa_1.uuid,
                **self._default_params(datetime.timedelta(minutes=10)),
            )
            isa_1.version = mutated_isa.dss_query.isa.version

    def step2(self):
        """Can create Subscription in all DSSs, ISA accessible from all
        non-primary DSSs."""

        isa_1 = self._context["isa_1"]

        for index, dss in enumerate([self._dss_primary] + self._dss_others):

            with self.check(
                "Subscription[n] created with proper response", [dss.participant_id]
            ) as check:
                sub_1 = self._new_sub(f"sub_1_{index}")

                created_sub = dss.put_sub(
                    check,
                    sub_id=sub_1.uuid,
                    **self._default_params(datetime.timedelta(minutes=10)),
                )
                sub_1.version = created_sub.subscription.version

            with self.check(
                "service_areas includes ISA from S1", [dss.participant_id]
            ) as check:
                sub_isa: Optional[ISA] = next(
                    filter(lambda isa: isa.id == isa_1.uuid, created_sub.isas), None
                )

                if sub_isa is None:
                    check.record_failed(
                        summary=f"DSS did not return ISA {isa_1.uuid} from testStep1 when creating Subscription {sub_1.uuid}",
                        details=f"service_areas IDs: {', '.join([isa.id for isa in created_sub.isas])}",
                        query_timestamps=[created_sub.query.request.timestamp],
                    )

            # check data synchronization
            if index == 0:
                # the primary DSS should be the first we encounter
                primary_isa = sub_isa
                continue
            else:
                other_isa = sub_isa

            def get_fail_params(
                field_name: str,
                primary_isa_field_value: str,
                other_isa_field_value: object,
            ) -> dict:
                return dict(
                    summary=f"ISA[{dss.participant_id}].{field_name} not equal ISA[{self._dss_primary.participant_id}].{field_name}",
                    details=f"ISA[{dss.participant_id}].{field_name} is {primary_isa_field_value}; ISA[{self._dss_primary.participant_id}].{field_name} is {other_isa_field_value}",
                    query_timestamps=[created_sub.query.request.timestamp],
                )

            with self.check(
                "ID of ISA from S1 is properly synchronized with all DSS",
                [dss.participant_id],
            ) as check:
                if primary_isa.id != other_isa.id:
                    check.record_failed(
                        **get_fail_params("id", primary_isa.id, other_isa.id)
                    )

                if primary_isa.version != other_isa.version:
                    check.record_failed(
                        **get_fail_params(
                            "version", primary_isa.version, other_isa.version
                        )
                    )

            with self.check(
                "Owner of ISA from S1 is properly synchronized with all DSS",
                [dss.participant_id],
            ) as check:
                if primary_isa.owner != other_isa.owner:
                    check.record_failed(
                        **get_fail_params("owner", primary_isa.owner, other_isa.owner)
                    )

            with self.check(
                "URL of ISA from S1 is properly synchronized with all DSS",
                [dss.participant_id],
            ) as check:
                if primary_isa.flights_url != other_isa.flights_url:
                    check.record_failed(
                        **get_fail_params(
                            "flights_url",
                            primary_isa.flights_url,
                            other_isa.flights_url,
                        )
                    )

            with self.check(
                "Start/end times of ISA from S1 are properly synchronized with all DSS",
                [dss.participant_id],
            ) as check:
                if primary_isa.time_start != other_isa.time_start:
                    check.record_failed(
                        **get_fail_params(
                            "time_start",
                            str(primary_isa.time_start),
                            str(other_isa.time_start),
                        )
                    )

                if primary_isa.time_end != other_isa.time_end:
                    check.record_failed(
                        **get_fail_params(
                            "time_end",
                            str(primary_isa.time_end),
                            str(other_isa.time_end),
                        )
                    )

    def step3(self):
        """Can retrieve specific Subscription created in primary DSS
        from all DSSs."""

        sub_1_0 = self._context["sub_1_0"]

        with self.check(
            "Subscription[P] returned with proper response",
            [self._dss_primary.participant_id],
        ) as check:
            primary_sub = self._dss_primary.get_sub(
                check,
                sub_1_0.uuid,
            )

        for dss in self._dss_others:
            with self.check(
                "Subscription[P] returned with proper response", [dss.participant_id]
            ) as check:
                other_sub = dss.get_sub(
                    check,
                    sub_1_0.uuid,
                )

            # check data synchronization
            def get_fail_params(
                field_name: str,
                primary_sub_field_value: str,
                other_sub_field_value: object,
            ) -> dict:
                return dict(
                    summary=f"Subscription[{dss.participant_id}].{field_name} not equal Subscription[{self._dss_primary.participant_id}].{field_name}",
                    details=f"Subscription[{dss.participant_id}].{field_name} is {primary_sub_field_value}; Subscription[{self._dss_primary.participant_id}].{field_name} is {other_sub_field_value}",
                    query_timestamps=[other_sub.query.request.timestamp],
                )

            with self.check(
                "Subscription[P] ID is properly synchronized with all DSS",
                [dss.participant_id],
            ) as check:
                if primary_sub.subscription.id != other_sub.subscription.id:
                    check.record_failed(
                        **get_fail_params(
                            "id", primary_sub.subscription.id, other_sub.subscription.id
                        )
                    )

                if primary_sub.subscription.version != other_sub.subscription.version:
                    check.record_failed(
                        **get_fail_params(
                            "version",
                            primary_sub.subscription.version,
                            other_sub.subscription.version,
                        )
                    )

            with self.check(
                "Subscription[P] owner is properly synchronized with all DSS",
                [dss.participant_id],
            ) as check:
                if (
                    primary_sub.subscription.raw.owner
                    != other_sub.subscription.raw.owner
                ):
                    check.record_failed(
                        **get_fail_params(
                            "owner",
                            primary_sub.subscription.raw.owner,
                            other_sub.subscription.raw.owner,
                        )
                    )

            with self.check(
                "Subscription[P] URL is properly synchronized with all DSS",
                [dss.participant_id],
            ) as check:
                if primary_sub.subscription.isa_url != other_sub.subscription.isa_url:
                    check.record_failed(
                        **get_fail_params(
                            "isa_url",
                            primary_sub.subscription.isa_url,
                            other_sub.subscription.isa_url,
                        )
                    )

            with self.check(
                "Subscription[P] notification count is properly synchronized with all DSS",
                [dss.participant_id],
            ) as check:
                if (
                    primary_sub.subscription.raw.notification_index
                    != other_sub.subscription.raw.notification_index
                ):
                    check.record_failed(
                        **get_fail_params(
                            "notification_index",
                            primary_sub.subscription.raw.notification_index,
                            other_sub.subscription.raw.notification_index,
                        )
                    )

            with self.check(
                "Subscription[P] start/end times are properly synchronized with all DSS",
                [dss.participant_id],
            ) as check:
                if (
                    primary_sub.subscription.time_start
                    != other_sub.subscription.time_start
                ):
                    check.record_failed(
                        **get_fail_params(
                            "time_start",
                            primary_sub.subscription.time_start,
                            other_sub.subscription.time_start,
                        )
                    )

                if primary_sub.subscription.time_end != other_sub.subscription.time_end:
                    check.record_failed(
                        **get_fail_params(
                            "time_end",
                            primary_sub.subscription.time_end,
                            other_sub.subscription.time_end,
                        )
                    )
            with self.check(
                "Subscription[n] search returned with proper response",
                [dss.participant_id],
            ) as check:
                searched_subs = dss.search_subs(check, self._area_vertices)
                if not searched_subs.success:
                    check.record_failed(
                        summary="Subscription search on secondary DSS failed",
                        details=f"Subscription search request on secondary DSS failed with HTTP code {searched_subs.status_code}: {searched_subs.errors}",
                        query_timestamps=[searched_subs.query.request.timestamp],
                    )

            with self.check(
                "Subscription[P] cell ID is properly synchronized with all DSS",
                self._dss_primary.participant_id,
            ) as check:
                if primary_sub.subscription.id not in searched_subs.subscriptions:
                    check.record_failed(
                        summary=f"Subscription {primary_sub.subscription.id} not returned by search on secondary DSS",
                        details=f"Subscription {primary_sub.subscription.id} was written to the primary DSS in a specific area and searched for in the same area on the secondary DSS, but was not found. "
                        f"This may indicate that the primary DSS failed to properly synchronize the Cell ID to the DAR.",
                        query_timestamps=[searched_subs.query.request.timestamp],
                    )

    def step4(self):
        """Can query all Subscriptions in area from all DSSs."""

        all_sub_1_ids = self._get_entities_by_prefix("sub_1_").keys()

        for index, dss in enumerate([self._dss_primary] + self._dss_others):
            with self.check(
                "Can query all Subscriptions in area from all DSSs",
                [dss.participant_id],
            ) as check:
                subs = dss.search_subs(check, self._area_vertices)

                returned_sub_ids = set([sub_id for sub_id in subs.subscriptions])
                missing_subs = all_sub_1_ids - returned_sub_ids

                if missing_subs:
                    check.record_failed(
                        summary=f"DSS returned too few subscriptions",
                        details=f"Missing: {', '.join(missing_subs)}",
                        query_timestamps=[subs.query.request.timestamp],
                    )

    def step5(self):
        """Can modify ISA in primary DSS, ISA modification triggers
        subscription notification requests"""

        isa_1 = self._context["isa_1"]
        sub_1_0 = self._context["sub_1_0"]

        with self.check(
            "Can get ISA from primary DSS", [self._dss_primary.participant_id]
        ) as check:
            isa = self._dss_primary.get_isa(check, isa_1.uuid)
            isa_1.version = isa.isa.version

        with self.check(
            "Can modify ISA in primary DSS", [self._dss_primary.participant_id]
        ) as check:
            mutated_isa_primary = self._dss_primary.put_isa(
                check,
                isa_id=isa_1.uuid,
                isa_version=isa_1.version,
                do_not_notify="https://testdummy.interuss.org",
                **self._default_params(datetime.timedelta(seconds=SHORT_WAIT_SEC)),
            )
            isa_1.version = mutated_isa_primary.dss_query.isa.version

        subs_to_notify_primary = []
        for subscriber in mutated_isa_primary.subscribers:
            for s in subscriber.raw.subscriptions:
                subs_to_notify_primary.append(s.subscription_id)

        with self.check(
            "ISA modification on primary DSS triggers subscription notification requests",
            [self._dss_primary.participant_id],
        ) as check:
            if sub_1_0.uuid not in subs_to_notify_primary:
                check.record_failed(
                    summary=f"Subscription {sub_1_0.uuid} was not notified of ISA modification",
                    details=f"Subscription {sub_1_0.uuid} was created on the primary DSS and should have been notified of the ISA modification that happened on the primary DSS, but was not.",
                )

        for sec_dss in self._dss_others:
            with self.check(
                "Can modify ISA on secondary DSS",
                [sec_dss.participant_id],
            ) as check:
                mutated_isa_sec = sec_dss.put_isa(
                    check,
                    isa_id=isa_1.uuid,
                    isa_version=isa_1.version,
                    do_not_notify="https://testdummy.interuss.org",
                    **self._default_params(datetime.timedelta(seconds=SHORT_WAIT_SEC)),
                )
                isa_1.version = mutated_isa_sec.dss_query.isa.version

            subs_to_notify_sec = []
            for subscriber in mutated_isa_sec.subscribers:
                for s in subscriber.raw.subscriptions:
                    subs_to_notify_sec.append(s.subscription_id)

            with self.check(
                "ISA modification on secondary DSS triggers subscription notification requests",
                [self._dss_primary.participant_id, sec_dss.participant_id],
            ) as check:
                if sub_1_0.uuid not in subs_to_notify_sec:
                    check.record_failed(
                        summary=f"Subscription {sub_1_0.uuid} was not notified of ISA modification",
                        details=f"Subscription {sub_1_0.uuid} was created on the primary DSS (participant_id={self._dss_primary.participant_id}) and should have been notified of the ISA modification (ID={isa_1.uuid}, version={isa_1.version}) that happened on the secondary DSS (participant_id={sec_dss}), but was not.",
                    )

    def step6(self):
        """Can delete all Subscription in primary DSS"""

        all_sub_1 = self._get_entities_by_prefix("sub_1_")

        for sub_1 in all_sub_1.values():
            with self.check(
                "Subscription[n] deleted with proper response",
                [self._dss_primary.participant_id],
            ) as check:
                _ = self._dss_primary.del_sub(
                    check, sub_id=sub_1.uuid, sub_version=sub_1.version
                )

    def step7(self):
        """Subscription deletion from ID index was effective on primary DSS"""

        for index, dss in enumerate([self._dss_primary] + self._dss_others):
            sub_1 = self._context[f"sub_1_{index}"]

            with self.check("404 with proper response", [dss.participant_id]) as check:
                dss.no_sub(check, sub_1.uuid)

    def step8(self):
        """Subscription deletion from geographic index was effective on primary DSS"""

        all_sub_1_ids = self._get_entities_by_prefix("sub_1_").keys()

        for dss in [self._dss_primary] + self._dss_others:

            with self.check(
                "Subscriptions queried successfully", [dss.participant_id]
            ) as check:
                subs = dss.search_subs(check, self._area_vertices)

            with self.check(
                "No Subscription[i] 1≤i≤n returned with proper response",
                [dss.participant_id],
            ) as check:
                found_deleted_sub = [
                    sub_id
                    for sub_id in subs.subscriptions.keys()
                    if sub_id in all_sub_1_ids
                ]

                if found_deleted_sub:
                    check.record_failed(
                        summary="Found deleted Subscriptions",
                        details=f"Deleted Subscriptions found: {found_deleted_sub}",
                        query_timestamps=[subs.query.request.timestamp],
                    )

    def step9(self):
        """Expired ISA automatically removed, ISA modifications
        accessible from all non-primary DSSs"""

        sleep(
            SHORT_WAIT_SEC,
            "ISA_1 needs to expire so we can check it is automatically removed",
        )

        isa_1 = self._context["isa_1"]

        for index, dss in enumerate([self._dss_primary] + self._dss_others):
            sub_2 = self._new_sub(f"sub_2_{index}")

            with self.check(
                "Subscription[n] created with proper response", [dss.participant_id]
            ) as check:
                created_sub = dss.put_sub(
                    check,
                    sub_id=sub_2.uuid,
                    **self._default_params(datetime.timedelta(seconds=SHORT_WAIT_SEC)),
                )
                sub_2.version = created_sub.subscription.version

            with self.check(
                "service_areas does not include ISA from S1", [dss.participant_id]
            ) as check:
                isa_ids = [isa.id for isa in created_sub.isas]

                if isa_1.uuid in isa_ids:
                    check.record_failed(
                        summary=f"DSS returned expired ISA {isa_1.uuid} when creating Subscription {sub_2.uuid}",
                        details=f"service_areas IDs: {', '.join(isa_ids)}",
                        query_timestamps=[created_sub.query.request.timestamp],
                    )

    def step10(self):
        """ISA creation triggers subscription notification requests"""

        isa_2 = self._new_isa("isa_2")
        all_sub_2_ids = self._get_entities_by_prefix("sub_2_").keys()

        with self.check(
            "ISA[P] created with proper response", [self._dss_primary.participant_id]
        ) as check:
            mutated_isa = self._dss_primary.put_isa(
                check,
                isa_id=isa_2.uuid,
                do_not_notify="https://testdummy.interuss.org",
                **self._default_params(datetime.timedelta(minutes=10)),
            )
            isa_2.version = mutated_isa.dss_query.isa.version

        with self.check(
            "All Subscription[i] 1≤i≤n returned in subscribers",
            [self._dss_primary.participant_id],
        ) as check:
            missing_subs = all_sub_2_ids - mutated_isa.dss_query.sub_ids

            if missing_subs:
                check.record_failed(
                    summary=f"DSS returned too few Subscriptions",
                    details=f"Missing Subscriptions: {', '.join(missing_subs)}",
                    query_timestamps=[mutated_isa.dss_query.query.request.timestamp],
                )

    def step11(self):
        """ISA deletion triggers subscription notification requests"""

        isa_2 = self._context["isa_2"]
        all_sub_2_ids = self._get_entities_by_prefix("sub_2_").keys()

        with self.check(
            "ISA[P] deleted with proper response", [self._dss_primary.participant_id]
        ) as check:
            del_isa = self._dss_primary.del_isa(
                check,
                isa_id=isa_2.uuid,
                isa_version=isa_2.version,
                do_not_notify="https://testdummy.interuss.org",
            )

        with self.check(
            "All Subscription[i] 1≤i≤n returned in subscribers",
            [self._dss_primary.participant_id],
        ) as check:
            missing_subs = all_sub_2_ids - del_isa.dss_query.sub_ids

            if missing_subs:
                check.record_failed(
                    summary=f"DSS returned too few Subscriptions",
                    details=f"Missing Subscriptions: {', '.join(missing_subs)}",
                    query_timestamps=[del_isa.dss_query.query.request.timestamp],
                )

    def step12(self):
        """Expired Subscriptions don’t trigger subscription notification requests"""

        sleep(
            SHORT_WAIT_SEC,
            "Subscriptions needs to expire so we can check they don't trigger notifications",
        )

        isa_3 = self._new_isa("isa_3")
        all_sub_2_ids = self._get_entities_by_prefix("sub_2_").keys()

        with self.check(
            "ISA[P] created with proper response", [self._dss_primary.participant_id]
        ) as check:
            mutated_isa = self._dss_primary.put_isa(
                check,
                isa_id=isa_3.uuid,
                **self._default_params(datetime.timedelta(minutes=10)),
            )
            isa_3.version = mutated_isa.dss_query.isa.version

        with self.check(
            "None of Subscription[i] 1≤i≤n returned in subscribers",
            [self._dss_primary.participant_id],
        ) as check:
            found_expired_sub = [
                sub_id
                for sub_id in mutated_isa.dss_query.sub_ids
                if sub_id in all_sub_2_ids
            ]

            if found_expired_sub:
                check.record_failed(
                    summary="Found expired Subscriptions",
                    details=f"Expired Subscriptions found: {', '.join(found_expired_sub)}",
                    query_timestamps=[mutated_isa.dss_query.query.request.timestamp],
                )

    def step13(self):
        """Expired Subscription removed from geographic index on primary DSS"""

        all_sub_2_ids = self._get_entities_by_prefix("sub_2_").keys()

        for index, dss in enumerate([self._dss_primary] + self._dss_others):
            with self.check(
                "Subscriptions queried successfully", [dss.participant_id]
            ) as check:
                subs = dss.search_subs(check, self._area_vertices)

            with self.check(
                "No Subscription[i] 1≤i≤n returned with proper response",
                [dss.participant_id],
            ) as check:
                found_expired_sub = [
                    sub_id
                    for sub_id in subs.subscriptions.keys()
                    if sub_id in all_sub_2_ids
                ]

                if found_expired_sub:
                    check.record_failed(
                        summary="Found expired Subscriptions",
                        details=f"Expired Subscriptions found: {', '.join(found_expired_sub)}",
                        query_timestamps=[subs.query.request.timestamp],
                    )

    def step14(self):
        """Expired Subscription still accessible shortly after expiration"""

        for index, dss in enumerate([self._dss_primary] + self._dss_others):
            # sub_2 = self._context[f"sub_2_{index}"]
            #
            # with self.check("404 with proper response", [dss.participant_id]) as check:
            #     dss.no_sub(check, sub_2.uuid)
            # TODO: Investigate expected behavior and "404 with proper response" check
            pass

    def step15(self):
        """ISA deletion does not trigger subscription
        notification requests for expired Subscriptions"""

        isa_3 = self._context["isa_3"]
        all_sub_2_ids = self._get_entities_by_prefix("sub_2_").keys()

        with self.check(
            "ISA[P] deleted with proper response", [self._dss_primary.participant_id]
        ) as check:
            del_isa = self._dss_primary.del_isa(
                check, isa_id=isa_3.uuid, isa_version=isa_3.version
            )

        with self.check(
            "None of Subscription[i] 1≤i≤n returned in subscribers with proper response",
            [self._dss_primary.participant_id],
        ) as check:
            found_expired_sub = [
                sub_id
                for sub_id in del_isa.dss_query.sub_ids
                if sub_id in all_sub_2_ids
            ]

            if found_expired_sub:
                check.record_failed(
                    summary="Found expired Subscriptions",
                    details=f"Expired Subscriptions found: {', '.join(found_expired_sub)}",
                    query_timestamps=[del_isa.dss_query.query.request.timestamp],
                )

    def step16(self):
        """Deleted ISA removed from all DSSs"""

        isa_3 = self._context["isa_3"]

        for index, dss in enumerate([self._dss_primary] + self._dss_others):
            sub_3 = self._new_sub(f"sub_3_{index}")

            with self.check(
                "Subscription[n] created with proper response", [dss.participant_id]
            ) as check:
                created_sub = dss.put_sub(
                    check,
                    sub_id=sub_3.uuid,
                    **self._default_params(datetime.timedelta(minutes=10)),
                )
                sub_3.version = created_sub.subscription.version

            with self.check(
                "service_areas does not include ISA from S12", [dss.participant_id]
            ) as check:
                isa_ids = [isa.id for isa in created_sub.isas]

                if isa_3.uuid in isa_ids:
                    check.record_failed(
                        summary=f"DSS returned expired ISA {isa_3.uuid} when creating Subscription {sub_3.uuid}",
                        details=f"service_areas IDs: {', '.join(isa_ids)}",
                        query_timestamps=[created_sub.query.request.timestamp],
                    )

    def step17(self):
        """Clean up SUBS_3"""

        all_sub_3 = self._get_entities_by_prefix("sub_3_").values()

        for sub_3 in all_sub_3:
            with self.check(
                "Subscription[n] deleted with proper response",
                [self._dss_primary.participant_id],
            ) as check:
                _ = self._dss_primary.del_sub(
                    check, sub_id=sub_3.uuid, sub_version=sub_3.version
                )

    def _default_params(self, duration: datetime.timedelta) -> Dict:
        now = datetime.datetime.now().astimezone()

        return dict(
            area_vertices=self._area_vertices,
            alt_lo=self._planning_area.volume.altitude_lower_wgs84_m(
                DEFAULT_LOWER_ALT_M
            ),
            alt_hi=self._planning_area.volume.altitude_upper_wgs84_m(
                DEFAULT_UPPER_ALT_M
            ),
            start_time=now,
            end_time=now + duration,
            uss_base_url=self._planning_area.get_base_url(),
        )

    def cleanup(self):
        self.begin_cleanup()

        for entity in self._context.values():
            if entity.type == EntityType.ISA:
                with self.check(
                    "ISA deleted with proper response",
                    [self._dss_primary.participant_id],
                ) as check:
                    _ = self._dss_primary.cleanup_isa(
                        check,
                        isa_id=entity.uuid,
                    )

            elif entity.type == EntityType.Sub:
                _ = self._dss_primary.cleanup_sub(
                    sub_id=entity.uuid,
                )

            else:
                raise RuntimeError(f"Unknown Entity type: {entity.type}")

        self.end_cleanup()
