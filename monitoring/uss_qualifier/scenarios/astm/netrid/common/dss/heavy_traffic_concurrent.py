import asyncio
from datetime import datetime

import s2sphere
from implicitdict import ImplicitDict
from uas_standards.astm.f3411 import v19, v22a

from monitoring.monitorlib.fetch import (
    Query,
    QueryType,
    fetch_async,
)
from monitoring.monitorlib.fetch.rid import FetchedISA
from monitoring.monitorlib.infrastructure import AsyncUTMTestSession
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.mutate.rid import ChangedISA
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.testing import make_fake_url
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.interuss.scenarios.astm.netrid.common.dss.heavy_traffic_concurrent import (
    HeavyTrafficConcurrentBehaviorResource,
    HeavyTrafficConcurrentBehaviorSpecification,
)
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss.isa_validator import (
    ISAValidator,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss.utils import (
    delete_isa_if_exists,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class ISAParams(ImplicitDict):
    area_vertices: list[s2sphere.LatLng]
    start_time: datetime | None
    end_time: datetime | None
    uss_base_url: str
    alt_lo: float
    alt_hi: float


class HeavyTrafficConcurrent(GenericTestScenario):
    """Based on prober/rid/v1/test_isa_simple_heavy_traffic_concurrent.py from the legacy prober tool."""

    ISA_TYPE = register_resource_type(374, "ISA")
    SUB_TYPE = register_resource_type(405, "Background subscription")

    _sub_id: str

    _isa_count: int

    _isa_ids: list[str]

    _isa_area: list[s2sphere.LatLng]

    _isa_params: ISAParams

    _isa_versions: dict[str, str]

    _async_session: AsyncUTMTestSession

    _semaphore: asyncio.Semaphore

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        isa: ServiceAreaResource,
        behavior_adjustment: HeavyTrafficConcurrentBehaviorResource | None = None,
    ):
        super().__init__()
        self._dss = (
            dss.dss_instance
        )  # TODO: delete once _delete_isa_if_exists updated to use dss_wrapper
        self._dss_wrapper = DSSWrapper(self, dss.dss_instance)

        behavior = (
            behavior_adjustment.value
            if behavior_adjustment
            else HeavyTrafficConcurrentBehaviorSpecification()
        )

        self._isa_versions: dict[str, str] = {}
        self._isa = isa
        self._isa_area = isa.s2_vertices()

        # Note that when the test scenario ends prematurely, we may end up with an unclosed session.
        self._async_session = AsyncUTMTestSession(
            self._dss.base_url, self._dss.client.auth_adapter
        )

        self._sub_id = id_generator.id_factory.make_id(HeavyTrafficConcurrent.SUB_TYPE)

        isa_base_id = id_generator.id_factory.make_id(HeavyTrafficConcurrent.ISA_TYPE)
        # The base ID ends in 000: we simply increment it to generate the other IDs
        self._isa_ids = [
            f"{isa_base_id[:-3]}{i:03d}" for i in range(behavior.isa_count)
        ]

        # currently all params are the same:
        # we could improve the test by having unique parameters per ISA
        self._isa_params = ISAParams(
            area_vertices=self._isa_area,
            start_time=None,
            end_time=None,
            uss_base_url=self._isa.base_url,
            alt_lo=self._isa.altitude_min,
            alt_hi=self._isa.altitude_max,
        )

        self._semaphore = asyncio.Semaphore(behavior.concurrency)

    def run(self, context: ExecutionContext):
        self._resolve_isa_time_bounds()

        self.begin_test_scenario(context)

        self.begin_test_case("Setup")
        self.begin_test_step("Ensure clean workspace")
        self._delete_isas_if_exists()
        self.end_test_step()
        self.begin_test_step("Emplace subscription")
        self._create_subscription()
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Concurrent Requests")

        self.begin_test_step("Create ISA concurrently")
        self._create_isas_concurrent_step()
        self.end_test_step()

        self.begin_test_step("Get ISAs concurrently")
        self._get_isas_by_id_concurrent_step()
        self.end_test_step()

        self.begin_test_step("Search Available ISAs")
        self._search_area_step()
        self.end_test_step()

        self.begin_test_step("Delete ISAs concurrently")
        self._delete_isas()
        self.end_test_step()

        self.begin_test_step("Access Deleted ISAs")
        self._get_deleted_isas()
        self.end_test_step()

        self.begin_test_step("Search Deleted ISAs")
        self._search_deleted_isas()
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _resolve_isa_time_bounds(self):
        start, end = self._isa.resolved_time_bounds(self.time_context.evaluate_now())
        self._isa_params.start_time = start
        self._isa_params.end_time = end

    def _create_subscription(self):
        with self.check(
            "Subscription creation succeeds", self._dss_wrapper.participant_id
        ) as check:
            cs = self._dss_wrapper.put_sub(
                check,
                self._isa_params.area_vertices,
                self._isa_params.alt_lo,
                self._isa_params.alt_hi,
                self._isa_params.start_time,
                self._isa_params.end_time,
                make_fake_url("preexisting_sub"),
                self._sub_id,
                None,
            )
            if not cs.success:
                check.record_failed(
                    summary="Error while creating a Subscription in the DSS",
                    details=f"Error message: {cs.errors}",
                    query_timestamps=cs.query_timestamps,
                )

    def _delete_isas_if_exists(self):
        """Delete test ISAs if they exist. Done sequentially."""
        for isa_id in self._isa_ids:
            delete_isa_if_exists(
                self,
                isa_id=isa_id,
                rid_version=self._dss.rid_version,
                session=self._dss.client,
                participant_id=self._dss_wrapper.participant_id,
            )

    def _get_isas_by_id_concurrent_step(self):
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            asyncio.gather(*[self._get_isa(isa_id) for isa_id in self._isa_ids])
        )

        for _, fetched_isa in results:
            self.record_query(fetched_isa.query)

        with self.check(
            "Successful Concurrent ISA query", [self._dss_wrapper.participant_id]
        ) as main_check:
            for isa_id, fetched_isa in results:
                if fetched_isa.status_code != 200:
                    main_check.record_failed(
                        f"ISA retrieval query failed for {isa_id}",
                        details=f"ISA retrieval query for {isa_id} yielded code {fetched_isa.status_code}",
                        queries=fetched_isa.query,
                    )

            isa_validator = ISAValidator(
                main_check=main_check,
                scenario=self,
                isa_params=self._isa_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
            )

            for isa_id, fetched_isa in results:
                if fetched_isa.status_code == 200:
                    isa_validator.validate_fetched_isa(
                        isa_id, fetched_isa, expected_version=self._isa_versions[isa_id]
                    )

    def _wrap_isa_get_query(self, q: Query) -> FetchedISA:
        """Wrap things into the correct utility class"""
        if self._dss.rid_version == RIDVersion.f3411_19:
            return FetchedISA(v19_query=q)
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            return FetchedISA(v22a_query=q)
        else:
            raise ValueError(f"Unsupported RID version '{self._dss.rid_version}'")

    def _wrap_isa_put_query(self, q: Query, mutation: str) -> ChangedISA:
        """Wrap things into the correct utility class"""
        if self._dss.rid_version == RIDVersion.f3411_19:
            return ChangedISA(mutation=mutation, v19_query=q)
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            return ChangedISA(mutation=mutation, v22a_query=q)
        else:
            raise ValueError(f"Unsupported RID version '{self._dss.rid_version}'")

    async def _get_isa(self, isa_id):
        async with self._semaphore:
            (_, url) = mutate.build_isa_url(self._dss.rid_version, isa_id)
            rq = await fetch_async.query_and_describe(
                self._async_session,
                "GET",
                url,
                scope=self._read_scope(),
                participant_id=self._dss.participant_id,
                query_type=QueryType.dss_get_isa(self._dss.rid_version),
            )
            return isa_id, self._wrap_isa_get_query(rq)

    async def _create_isa(self, isa_id):
        async with self._semaphore:
            payload = mutate.build_isa_request_body(
                **self._isa_params,
                rid_version=self._dss.rid_version,
            )
            (_, url) = mutate.build_isa_url(self._dss.rid_version, isa_id)
            rq = await fetch_async.query_and_describe(
                self._async_session,
                "PUT",
                url,
                json=payload,
                scope=self._write_scope(),
                participant_id=self._dss.participant_id,
                query_type=QueryType.dss_create_isa(self._dss.rid_version),
            )
            return isa_id, self._wrap_isa_put_query(rq, "create")

    async def _delete_isa(self, isa_id, isa_version):
        async with self._semaphore:
            (_, url) = mutate.build_isa_url(self._dss.rid_version, isa_id, isa_version)
            rq = await fetch_async.query_and_describe(
                self._async_session,
                "DELETE",
                url,
                scope=self._write_scope(),
                participant_id=self._dss.participant_id,
                query_type=QueryType.dss_delete_isa(self._dss.rid_version),
            )
            return isa_id, self._wrap_isa_put_query(rq, "delete")

    def _write_scope(self):
        if self._dss.rid_version == RIDVersion.f3411_19:
            return v19.constants.Scope.Write
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            return v22a.constants.Scope.ServiceProvider
        else:
            raise ValueError(f"Unsupported RID version '{self._dss.rid_version}'")

    def _read_scope(self):
        if self._dss.rid_version == RIDVersion.f3411_19:
            return v19.constants.Scope.Read
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            return v22a.constants.Scope.DisplayProvider
        else:
            raise ValueError(f"Unsupported RID version '{self._dss.rid_version}'")

    def _create_isas_concurrent_step(self):
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            asyncio.gather(*[self._create_isa(isa_id) for isa_id in self._isa_ids])
        )

        for _, fetched_isa in results:
            self.record_query(fetched_isa.query)

        with self.check(
            "Concurrent ISAs creation", [self._dss_wrapper.participant_id]
        ) as main_check:
            for isa_id, changed_isa in results:
                with self.check(
                    "ISA response code", [self._dss_wrapper.participant_id]
                ) as sub_check:
                    if changed_isa.status_code == 201:
                        sub_check.record_failed(
                            summary="PUT ISA returned technically-incorrect 201",
                            details="DSS should return 200 from PUT ISA, but instead returned the reasonable-but-technically-incorrect code 201",
                            queries=changed_isa.query,
                        )
                if changed_isa.status_code not in [200, 201]:
                    main_check.record_failed(
                        f"ISA creation failed for {isa_id}",
                        details=f"ISA creation for {isa_id} returned {changed_isa.status_code}",
                        queries=changed_isa.query,
                    )
                else:
                    self._isa_versions[isa_id] = changed_isa.isa.version

            isa_validator = ISAValidator(
                main_check=main_check,
                scenario=self,
                isa_params=self._isa_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
            )

            for isa_id, changed_isa in results:
                if changed_isa.status_code in [200, 201]:
                    isa_validator.validate_mutated_isa(
                        isa_id, changed_isa, previous_version=None
                    )

    def _search_area_step(self):
        with self.check(
            "Successful ISAs search", [self._dss_wrapper.participant_id]
        ) as main_check:
            isas = self._dss_wrapper.search_isas(
                main_check,
                area=self._isa_area,
            )

            with self.check(
                "Correct ISAs returned by search", [self._dss_wrapper.participant_id]
            ) as sub_check:
                for isa_id in self._isa_ids:
                    if isa_id not in isas.isas.keys():
                        sub_check.record_failed(
                            f"ISAs search did not return ISA {isa_id} that was just created",
                            details=f"Search in area {self._isa_area} returned ISAs {isas.isas.keys()} and is missing some of the created ISAs",
                            queries=isas.query,
                        )

            isa_validator = ISAValidator(
                main_check=main_check,
                scenario=self,
                isa_params=self._isa_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
            )

            isa_validator.validate_searched_isas(
                isas, expected_versions=self._isa_versions
            )

    def _delete_isas(self):
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            asyncio.gather(
                *[
                    self._delete_isa(isa_id, self._isa_versions[isa_id])
                    for isa_id in self._isa_ids
                ]
            )
        )

        for _, fetched_isa in results:
            self.record_query(fetched_isa.query)

        with self.check(
            "ISAs deletion query success", [self._dss_wrapper.participant_id]
        ) as main_check:
            for isa_id, deleted_isa in results:
                if deleted_isa.status_code != 200:
                    main_check.record_failed(
                        f"ISA deletion failed for {isa_id}",
                        details=f"ISA deletion for {isa_id} returned {deleted_isa.status_code}",
                        queries=deleted_isa.query,
                    )

            isa_validator = ISAValidator(
                main_check=main_check,
                scenario=self,
                isa_params=self._isa_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
            )

            for isa_id, changed_isa in results:
                if changed_isa.status_code == 200:
                    isa_validator.validate_deleted_isa(
                        isa_id, changed_isa, expected_version=self._isa_versions[isa_id]
                    )

    def _get_deleted_isas(self):
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            asyncio.gather(*[self._get_isa(isa_id) for isa_id in self._isa_ids])
        )

        for _, fetched_isa in results:
            self.record_query(fetched_isa.query)

        with self.check("ISAs not found", [self._dss_wrapper.participant_id]) as check:
            for isa_id, fetched_isa in results:
                if fetched_isa.status_code != 404:
                    check.record_failed(
                        f"ISA retrieval succeeded for {isa_id}",
                        details=f"ISA retrieval for {isa_id} returned {fetched_isa.status_code}",
                        queries=fetched_isa.query,
                    )

    def _search_deleted_isas(self):
        with self.check(
            "Successful ISAs search", [self._dss_wrapper.participant_id]
        ) as check:
            isas = self._dss_wrapper.search_isas(
                check,
                area=self._isa_area,
            )

        with self.check(
            "ISAs not returned by search", [self._dss_wrapper.participant_id]
        ) as check:
            for isa_id in self._isa_ids:
                if isa_id in isas.isas.keys():
                    check.record_failed(
                        f"ISAs search returned deleted ISA {isa_id}",
                        details=f"Search in area {self._isa_area} returned ISAs {isas.isas.keys()} that contained some of the ISAs we had previously deleted.",
                        queries=isas.query,
                    )

    def cleanup(self):
        self.begin_cleanup()

        self._dss_wrapper.cleanup_sub(self._sub_id)
        self._delete_isas_if_exists()
        self._async_session.close()

        self.end_cleanup()
