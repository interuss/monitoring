import asyncio
import typing
from datetime import datetime
from typing import List, Dict

import arrow
import requests
from uas_standards.astm.f3411 import v19, v22a

from monitoring.monitorlib.fetch import (
    describe_request,
    Query,
    describe_aiohttp_response,
)
from monitoring.monitorlib.fetch.rid import FetchedISA
from monitoring.monitorlib.infrastructure import AsyncUTMTestSession
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.mutate.rid import ChangedISA
from monitoring.monitorlib.rid import RIDVersion
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
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

# Semaphore is added to limit the number of simultaneous requests.
# TODO add these to an optional resource to allow overriding them.
SEMAPHORE = asyncio.Semaphore(20)
THREAD_COUNT = 10
CREATE_ISAS_COUNT = 100


class HeavyTrafficConcurrent(GenericTestScenario):
    """Based on prober/rid/v1/test_isa_simple_heavy_traffic_concurrent.py from the legacy prober tool."""

    ISA_TYPE = register_resource_type(374, "ISA")

    _isa_ids: List[str]

    _isa_params: Dict[str, any]

    _isa_versions: Dict[str, str]

    _async_session: AsyncUTMTestSession

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

        self._isa_versions: Dict[str, str] = {}
        self._isa = isa.specification

        now = arrow.utcnow().datetime
        self._isa_start_time = self._isa.shifted_time_start(now)
        self._isa_end_time = self._isa.shifted_time_end(now)
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]

        # Note that when the test scenario ends prematurely, we may end up with an unclosed session.
        self._async_session = AsyncUTMTestSession(
            self._dss.base_url, self._dss.client.auth_adapter
        )

        isa_base_id = id_generator.id_factory.make_id(HeavyTrafficConcurrent.ISA_TYPE)
        # The base ID ends in 000: we simply increment it to generate the other IDs
        self._isa_ids = [f"{isa_base_id[:-3]}{i:03d}" for i in range(CREATE_ISAS_COUNT)]

        # currently all params are the same:
        # we could improve the test by having unique parameters per ISA
        self._isa_params = dict(
            area_vertices=self._isa_area,
            start_time=self._isa_start_time,
            end_time=self._isa_end_time,
            uss_base_url=self._isa.base_url,
            alt_lo=self._isa.altitude_min,
            alt_hi=self._isa.altitude_max,
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Setup")
        self.begin_test_step("Ensure clean workspace")
        self._delete_isas_if_exists()
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

        results = typing.cast(Dict[str, FetchedISA], results)

        for _, fetched_isa in results:
            self.record_query(fetched_isa.query)

        with self.check(
            "Successful Concurrent ISA query", [self._dss_wrapper.participant_id]
        ) as main_check:
            for isa_id, fetched_isa in results:
                if fetched_isa.status_code != 200:
                    main_check.record_failed(
                        f"ISA retrieval query failed for {isa_id}",
                        severity=Severity.High,
                        details=f"ISA retrieval query for {isa_id} yielded code {fetched_isa.status_code}",
                    )

            isa_validator = ISAValidator(
                main_check=main_check,
                scenario=self,
                isa_params=self._isa_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
            )

            for isa_id, fetched_isa in results:
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
        async with SEMAPHORE:
            (_, url) = mutate.build_isa_url(self._dss.rid_version, isa_id)
            # Build a `Request` object to register the query later on,
            # although we don't need it to do the effective request here on the async_session
            # This one is quite barebone and we need to check if anything needs to be added
            r = requests.Request(
                "GET",
                url,
            )
            prep = self._dss.client.prepare_request(r)
            t0 = datetime.utcnow()
            req_descr = describe_request(prep, t0)
            status, headers, resp_json = await self._async_session.get(
                url=url, scope=self._read_scope()
            )
            duration = datetime.utcnow() - t0
            rq = Query(
                request=req_descr,
                response=describe_aiohttp_response(
                    status, headers, resp_json, duration
                ),
                participant_id=self._dss.participant_id,
            )
            return isa_id, self._wrap_isa_get_query(rq)

    async def _create_isa(self, isa_id):
        async with SEMAPHORE:
            payload = mutate.build_isa_request_body(
                **self._isa_params,
                rid_version=self._dss.rid_version,
            )
            (_, url) = mutate.build_isa_url(self._dss.rid_version, isa_id)
            r = requests.Request(
                "PUT",
                url,
                json=payload,
            )
            prep = self._dss.client.prepare_request(r)
            t0 = datetime.utcnow()
            req_descr = describe_request(prep, t0)
            status, headers, resp_json = await self._async_session.put(
                url=url, json=payload, scope=self._write_scope()
            )
            duration = datetime.utcnow() - t0
            rq = Query(
                request=req_descr,
                response=describe_aiohttp_response(
                    status, headers, resp_json, duration
                ),
                participant_id=self._dss.participant_id,
            )
            return isa_id, self._wrap_isa_put_query(rq, "create")

    async def _delete_isa(self, isa_id, isa_version):
        async with SEMAPHORE:
            (_, url) = mutate.build_isa_url(self._dss.rid_version, isa_id, isa_version)
            r = requests.Request(
                "DELETE",
                url,
            )
            prep = self._dss.client.prepare_request(r)
            t0 = datetime.utcnow()
            req_descr = describe_request(prep, t0)
            status, headers, resp_json = await self._async_session.delete(
                url=url, scope=self._write_scope()
            )
            duration = datetime.utcnow() - t0
            rq = Query(
                request=req_descr,
                response=describe_aiohttp_response(
                    status, headers, resp_json, duration
                ),
                participant_id=self._dss.participant_id,
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

        results = typing.cast(Dict[str, ChangedISA], results)

        for _, fetched_isa in results:
            self.record_query(fetched_isa.query)

        with self.check(
            "Concurrent ISAs creation", [self._dss_wrapper.participant_id]
        ) as main_check:
            for isa_id, changed_isa in results:
                if changed_isa.query.response.code != 200:
                    main_check.record_failed(
                        f"ISA creation failed for {isa_id}",
                        severity=Severity.High,
                        details=f"ISA creation for {isa_id} returned {changed_isa.query.response.code}",
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
                            severity=Severity.High,
                            details=f"Search in area {self._isa_area} returned ISAs {isas.isas.keys()} and is missing some of the created ISAs",
                            query_timestamps=[isas.dss_query.query.request.timestamp],
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

        results = typing.cast(Dict[str, ChangedISA], results)

        for _, fetched_isa in results:
            self.record_query(fetched_isa.query)

        with self.check(
            "ISAs deletion query success", [self._dss_wrapper.participant_id]
        ) as main_check:
            for isa_id, deleted_isa in results:
                if deleted_isa.query.response.code != 200:
                    main_check.record_failed(
                        f"ISA deletion failed for {isa_id}",
                        severity=Severity.High,
                        details=f"ISA deletion for {isa_id} returned {deleted_isa.query.response.code}",
                    )

            isa_validator = ISAValidator(
                main_check=main_check,
                scenario=self,
                isa_params=self._isa_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
            )

            for isa_id, changed_isa in results:
                isa_validator.validate_deleted_isa(
                    isa_id, changed_isa, expected_version=self._isa_versions[isa_id]
                )

    def _get_deleted_isas(self):

        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            asyncio.gather(*[self._get_isa(isa_id) for isa_id in self._isa_ids])
        )

        results = typing.cast(Dict[str, ChangedISA], results)

        for _, fetched_isa in results:
            self.record_query(fetched_isa.query)

        with self.check("ISAs not found", [self._dss_wrapper.participant_id]) as check:
            for isa_id, fetched_isa in results:
                if fetched_isa.status_code != 404:
                    check.record_failed(
                        f"ISA retrieval succeeded for {isa_id}",
                        severity=Severity.High,
                        details=f"ISA retrieval for {isa_id} returned {fetched_isa.status_code}",
                        query_timestamps=[fetched_isa.query.request.timestamp],
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
                        severity=Severity.High,
                        details=f"Search in area {self._isa_area} returned ISAs {isas.isas.keys()} that contained some of the ISAs we had previously deleted.",
                        query_timestamps=[isas.dss_query.query.request.timestamp],
                    )

    def cleanup(self):
        self.begin_cleanup()

        self._delete_isas_if_exists()
        self._async_session.close()

        self.end_cleanup()
