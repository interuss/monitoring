import ipaddress
import socket
import time
import uuid
from dataclasses import dataclass
import datetime
from enum import Enum
from typing import List, Dict, Optional
from urllib.parse import urlparse

import s2sphere

from monitoring.monitorlib.fetch.rid import ISA
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import (
    DSSInstancesResource,
    DSSInstanceResource,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

VERTICES: List[s2sphere.LatLng] = [
    s2sphere.LatLng.from_degrees(lng=130.6205, lat=-23.6558),
    s2sphere.LatLng.from_degrees(lng=130.6301, lat=-23.6898),
    s2sphere.LatLng.from_degrees(lng=130.6700, lat=-23.6709),
    s2sphere.LatLng.from_degrees(lng=130.6466, lat=-23.6407),
]


def _default_params(duration: datetime.timedelta) -> Dict:
    now = datetime.datetime.now().astimezone()
    return dict(
        area_vertices=VERTICES,
        alt_lo=20,
        alt_hi=400,
        start_time=now,
        end_time=now + duration,
        uss_base_url="https://example.com",
    )


SHORT_WAIT_SEC = 5


class EntityType(str, Enum):
    ISA = "ISA"
    Sub = "Sub"


@dataclass
class TestEntity(object):
    type: EntityType
    uuid: str
    version: Optional[str] = None


class DSSInteroperability(GenericTestScenario):
    _dss_primary: DSSWrapper
    _dss_others: List[DSSWrapper]
    _context: Dict[str, TestEntity]

    def __init__(
        self,
        primary_dss_instance: DSSInstanceResource,
        all_dss_instances: DSSInstancesResource,
    ):
        super().__init__()
        self._dss_primary = DSSWrapper(self, primary_dss_instance.dss_instance)
        self._dss_others = [
            DSSWrapper(self, dss)
            for dss in all_dss_instances.dss_instances
            if not dss.is_same_as(primary_dss_instance.dss_instance)
        ]
        self._context: Dict[str, TestEntity] = {}

    def _new_isa(self, name: str) -> TestEntity:
        self._context[name] = TestEntity(EntityType.ISA, str(uuid.uuid4()))
        return self._context[name]

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

                if dss.has_private_address:
                    self.record_note(
                        f"{dss.participant_id}_private_address",
                        f"DSS instance (URL: {dss.base_url}, netloc: {parsed_url.netloc}, resolved IP: {ip_addr}) is declared as explicitly having a private address, skipping check",
                    )
                elif ipaddress.ip_address(ip_addr).is_private:
                    check.record_failed(
                        summary=f"DSS host {parsed_url.netloc} is not publicly addressable",
                        severity=Severity.Medium,
                        details=f"DSS (URL: {dss.base_url}, netloc: {parsed_url.netloc}, resolved IP: {ip_addr}) is not publicly addressable",
                    )

            with self.check("DSS instance is reachable", [dss.participant_id]) as check:
                # dummy search query
                dss.search_subs(check, VERTICES)

    def step1(self):
        """Create ISA in Primary DSS with 10 min TTL."""

        with self.check(
            "ISA[P] created with proper response", [self._dss_primary.participant_id]
        ) as check:
            isa_1 = self._new_isa("isa_1")

            mutated_isa = self._dss_primary.put_isa(
                check,
                isa_id=isa_1.uuid,
                **_default_params(datetime.timedelta(minutes=10)),
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
                    **_default_params(datetime.timedelta(minutes=10)),
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
                        severity=Severity.High,
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
                    severity=Severity.High,
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
        """Can retrieve specific Subscription emplaced in primary DSS
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
                    severity=Severity.High,
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

    def step4(self):
        """Can query all Subscriptions in area from all DSSs."""

        all_sub_1_ids = self._get_entities_by_prefix("sub_1_").keys()

        for index, dss in enumerate([self._dss_primary] + self._dss_others):
            with self.check(
                "Can query all Subscriptions in area from all DSSs",
                [dss.participant_id],
            ) as check:
                subs = dss.search_subs(check, VERTICES)

                returned_sub_ids = set([sub_id for sub_id in subs.subscriptions])
                missing_subs = all_sub_1_ids - returned_sub_ids

                if missing_subs:
                    check.record_failed(
                        summary=f"DSS returned too few subscriptions",
                        severity=Severity.High,
                        details=f"Missing: {', '.join(missing_subs)}",
                        query_timestamps=[subs.query.request.timestamp],
                    )

    def step5(self):
        """Can modify ISA in primary DSS, ISA modification triggers
        subscription notification requests"""

        isa_1 = self._context["isa_1"]

        with self.check(
            "Can get ISA from primary DSS", [self._dss_primary.participant_id]
        ) as check:
            isa = self._dss_primary.get_isa(check, isa_1.uuid)
            isa_1.version = isa.isa.version

        with self.check(
            "Can modify ISA in primary DSS", [self._dss_primary.participant_id]
        ) as check:
            mutated_isa = self._dss_primary.put_isa(
                check,
                isa_id=isa_1.uuid,
                isa_version=isa_1.version,
                **_default_params(datetime.timedelta(seconds=SHORT_WAIT_SEC)),
            )
            isa_1.version = mutated_isa.dss_query.isa.version

        # TODO: Implement "ISA modification triggers subscription notification requests check"

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
                subs = dss.search_subs(check, VERTICES)

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
                        severity=Severity.High,
                        details=f"Deleted Subscriptions found: {found_deleted_sub}",
                        query_timestamps=[subs.query.request.timestamp],
                    )

    def step9(self):
        """Expired ISA automatically removed, ISA modifications
        accessible from all non-primary DSSs"""

        # sleep X seconds for ISA_1 to expire
        time.sleep(SHORT_WAIT_SEC)

        isa_1 = self._context["isa_1"]

        for index, dss in enumerate([self._dss_primary] + self._dss_others):
            sub_2 = self._new_sub(f"sub_2_{index}")

            with self.check(
                "Subscription[n] created with proper response", [dss.participant_id]
            ) as check:
                created_sub = dss.put_sub(
                    check,
                    sub_id=sub_2.uuid,
                    **_default_params(datetime.timedelta(seconds=SHORT_WAIT_SEC)),
                )
                sub_2.version = created_sub.subscription.version

            with self.check(
                "service_areas does not include ISA from S1", [dss.participant_id]
            ) as check:
                isa_ids = [isa.id for isa in created_sub.isas]

                if isa_1.uuid in isa_ids:
                    check.record_failed(
                        summary=f"DSS returned expired ISA {isa_1.uuid} when creating Subscription {sub_2.uuid}",
                        severity=Severity.High,
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
                **_default_params(datetime.timedelta(minutes=10)),
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
                    severity=Severity.High,
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
                check, isa_id=isa_2.uuid, isa_version=isa_2.version
            )

        with self.check(
            "All Subscription[i] 1≤i≤n returned in subscribers",
            [self._dss_primary.participant_id],
        ) as check:
            missing_subs = all_sub_2_ids - del_isa.dss_query.sub_ids

            if missing_subs:
                check.record_failed(
                    summary=f"DSS returned too few Subscriptions",
                    severity=Severity.High,
                    details=f"Missing Subscriptions: {', '.join(missing_subs)}",
                    query_timestamps=[del_isa.dss_query.query.request.timestamp],
                )

    def step12(self):
        """Expired Subscriptions don’t trigger subscription notification requests"""

        time.sleep(SHORT_WAIT_SEC)

        isa_3 = self._new_isa("isa_3")
        all_sub_2_ids = self._get_entities_by_prefix("sub_2_").keys()

        with self.check(
            "ISA[P] created with proper response", [self._dss_primary.participant_id]
        ) as check:
            mutated_isa = self._dss_primary.put_isa(
                check,
                isa_id=isa_3.uuid,
                **_default_params(datetime.timedelta(minutes=10)),
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
                    severity=Severity.High,
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
                subs = dss.search_subs(check, VERTICES)

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
                        severity=Severity.High,
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
                    severity=Severity.High,
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
                    **_default_params(datetime.timedelta(minutes=10)),
                )
                sub_3.version = created_sub.subscription.version

            with self.check(
                "service_areas does not include ISA from S12", [dss.participant_id]
            ) as check:
                isa_ids = [isa.id for isa in created_sub.isas]

                if isa_3.uuid in isa_ids:
                    check.record_failed(
                        summary=f"DSS returned expired ISA {isa_3.uuid} when creating Subscription {sub_3.uuid}",
                        severity=Severity.High,
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
