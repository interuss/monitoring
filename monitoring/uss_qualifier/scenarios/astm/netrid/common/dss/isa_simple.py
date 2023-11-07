from typing import Optional, List

import arrow
import s2sphere
import datetime

from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.resources import VerticesResource
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class ISASimple(GenericTestScenario):
    """Based on prober/rid/v2/test_isa_simple.py from the legacy prober tool."""

    ISA_TYPE = register_resource_type(348, "ISA")

    _huge_are: List[s2sphere.LatLng]

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        isa: ServiceAreaResource,
        problematically_big_area: VerticesResource,
    ):
        super().__init__()
        self._dss = (
            dss.dss_instance
        )  # TODO: delete once _delete_isa_if_exists updated to use dss_wrapper
        self._dss_wrapper = DSSWrapper(self, dss.dss_instance)
        self._isa_id = id_generator.id_factory.make_id(ISASimple.ISA_TYPE)
        self._isa_version: Optional[str] = None
        self._isa = isa.specification

        now = arrow.utcnow().datetime
        self._isa_start_time = self._isa.shifted_time_start(now)
        self._isa_end_time = self._isa.shifted_time_end(now)
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]
        self._huge_area = [
            v.as_s2sphere() for v in problematically_big_area.specification.vertices
        ]

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self._setup_case()
        self._create_and_check_isa_case()
        self._update_and_search_isa_case()
        self._delete_isa_case()

        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")

        def _ensure_clean_workspace_step():
            self.begin_test_step("Ensure clean workspace")

            self._delete_isa_if_exists()

            self.end_test_step()

        _ensure_clean_workspace_step()

        self.end_test_case()

    def _delete_isa_if_exists(self):
        fetched = fetch.isa(
            self._isa_id,
            rid_version=self._dss.rid_version,
            session=self._dss.client,
            participant_id=self._dss.participant_id,
        )
        self.record_query(fetched.query)
        with self.check("Successful ISA query", [self._dss.participant_id]) as check:
            if not fetched.success and fetched.status_code != 404:
                check.record_failed(
                    "ISA information could not be retrieved",
                    Severity.High,
                    f"{self._dss.participant_id} DSS instance returned {fetched.status_code} when queried for ISA {self._isa_id}",
                    query_timestamps=[fetched.query.request.timestamp],
                )

        if fetched.success:
            deleted = mutate.delete_isa(
                self._isa_id,
                fetched.isa.version,
                self._dss.rid_version,
                self._dss.client,
                participant_id=self._dss.participant_id,
            )
            self.record_query(deleted.dss_query.query)
            for subscriber_id, notification in deleted.notifications.items():
                self.record_query(notification.query)
            with self.check(
                "Removed pre-existing ISA", [self._dss.participant_id]
            ) as check:
                if not deleted.dss_query.success:
                    check.record_failed(
                        "Could not delete pre-existing ISA",
                        Severity.High,
                        f"Attempting to delete ISA {self._isa_id} from the {self._dss.participant_id} DSS returned error {deleted.dss_query.status_code}",
                        query_timestamps=[deleted.dss_query.query.request.timestamp],
                    )
            for subscriber_url, notification in deleted.notifications.items():
                # For checking the notifications, we ignore the request we made for the subscription that we created.
                if self._isa.base_url not in subscriber_url:
                    pid = (
                        notification.query.participant_id
                        if "participant_id" in notification.query
                        else None
                    )
                    with self.check(
                        "Notified subscriber", [pid] if pid else []
                    ) as check:
                        if not notification.success:
                            check.record_failed(
                                "Could not notify ISA subscriber",
                                Severity.Medium,
                                f"Attempting to notify subscriber for ISA {self._isa_id} at {subscriber_url} resulted in {notification.status_code}",
                                query_timestamps=[notification.query.request.timestamp],
                            )

    def _get_isa_by_id_step(self):
        self.begin_test_step("Get ISA by ID")

        with self.check(
            "Successful ISA query", [self._dss_wrapper.participant_id]
        ) as check:
            fetched = self._dss_wrapper.get_isa(check, self._isa_id)

        with self.check(
            "ISA version match", [self._dss_wrapper.participant_id]
        ) as check:
            if (
                self._isa_version is not None
                and fetched.isa.version != self._isa_version
            ):
                check.record_failed(
                    "DSS returned ISA with incorrect version",
                    Severity.High,
                    f"DSS should have returned an ISA with the version {self._isa_version}, but instead the ISA returned had the version {fetched.isa.version}",
                    query_timestamps=[fetched.query.request.timestamp],
                )

        self.end_test_step()

    def _create_and_check_isa_case(self):
        self.begin_test_case("Create and check ISA")

        def _create_isa_step():
            self.begin_test_step("Create ISA")

            with self.check("ISA created", [self._dss_wrapper.participant_id]) as check:
                isa_change = self._dss_wrapper.put_isa(
                    main_check=check,
                    area_vertices=self._isa_area,
                    start_time=self._isa_start_time,
                    end_time=self._isa_end_time,
                    uss_base_url=self._isa.base_url,
                    isa_id=self._isa_id,
                    isa_version=self._isa_version,
                    alt_lo=self._isa.altitude_min,
                    alt_hi=self._isa.altitude_max,
                )
                self._isa_version = isa_change.dss_query.isa.version

            self.end_test_step()

        _create_isa_step()

        self._get_isa_by_id_step()

        self.end_test_case()

    def _update_and_search_isa_case(self):
        self.begin_test_case("Update and search ISA")

        def _update_isa_step():
            self.begin_test_step("Update ISA")

            self._isa_end_time = self._isa_end_time + datetime.timedelta(seconds=1)
            with self.check("ISA updated", [self._dss_wrapper.participant_id]) as check:
                mutated_isa = self._dss_wrapper.put_isa(
                    check,
                    area_vertices=self._isa_area,
                    start_time=self._isa_start_time,
                    end_time=self._isa_end_time,
                    uss_base_url=self._isa.base_url,
                    isa_id=self._isa_id,
                    isa_version=self._isa_version,
                    alt_lo=self._isa.altitude_min,
                    alt_hi=self._isa.altitude_max,
                )
                self._isa_version = mutated_isa.dss_query.isa.version

            self.end_test_step()

        _update_isa_step()

        self._get_isa_by_id_step()

        def _search_earliest_incl_step():
            self.begin_test_step("Search by earliest time (included)")

            with self.check(
                "Successful ISAs search", [self._dss_wrapper.participant_id]
            ) as check:
                earliest = self._isa_end_time - datetime.timedelta(minutes=1)
                isas = self._dss_wrapper.search_isas(
                    check,
                    area=self._isa_area,
                    start_time=earliest,
                )

            with self.check(
                "ISA returned by search", [self._dss_wrapper.participant_id]
            ) as check:
                if self._isa_id not in isas.isas.keys():
                    check.record_failed(
                        f"ISAs search did not return expected ISA {self._isa_id}",
                        severity=Severity.High,
                        details=f"Search in area {self._isa_area} from time {earliest} returned ISAs {isas.isas.keys()}",
                        query_timestamps=[isas.dss_query.query.request.timestamp],
                    )

            self.end_test_step()

        _search_earliest_incl_step()

        def _search_earliest_excl_step():
            self.begin_test_step("Search by earliest time (excluded)")

            with self.check(
                "Successful ISAs search", [self._dss_wrapper.participant_id]
            ) as check:
                earliest = self._isa_end_time + datetime.timedelta(minutes=1)
                isas = self._dss_wrapper.search_isas(
                    check,
                    area=self._isa_area,
                    start_time=earliest,
                )

            with self.check(
                "ISA not returned by search", [self._dss_wrapper.participant_id]
            ) as check:
                if self._isa_id in isas.isas.keys():
                    check.record_failed(
                        f"ISAs search returned unexpected ISA {self._isa_id}",
                        severity=Severity.High,
                        details=f"Search in area {self._isa_area} from time {earliest} returned ISAs {isas.isas.keys()}",
                        query_timestamps=[isas.dss_query.query.request.timestamp],
                    )

            self.end_test_step()

        _search_earliest_excl_step()

        def _search_latest_incl_step():
            self.begin_test_step("Search by latest time (included)")

            with self.check(
                "Successful ISAs search", [self._dss_wrapper.participant_id]
            ) as check:
                latest = self._isa_start_time + datetime.timedelta(minutes=1)
                isas = self._dss_wrapper.search_isas(
                    check,
                    area=self._isa_area,
                    end_time=latest,
                )

            with self.check(
                "ISA returned by search", [self._dss_wrapper.participant_id]
            ) as check:
                if self._isa_id not in isas.isas.keys():
                    check.record_failed(
                        f"ISAs search did not return expected ISA {self._isa_id}",
                        severity=Severity.High,
                        details=f"Search in area {self._isa_area} to time {latest} returned ISAs {isas.isas.keys()}",
                        query_timestamps=[isas.dss_query.query.request.timestamp],
                    )

            self.end_test_step()

        _search_latest_incl_step()

        def _search_latest_excl_step():
            self.begin_test_step("Search by latest time (excluded)")

            with self.check(
                "Successful ISAs search", [self._dss_wrapper.participant_id]
            ) as check:
                latest = self._isa_start_time - datetime.timedelta(minutes=1)
                isas = self._dss_wrapper.search_isas(
                    check,
                    area=self._isa_area,
                    end_time=latest,
                )

            with self.check(
                "ISA not returned by search", [self._dss_wrapper.participant_id]
            ) as check:
                if self._isa_id in isas.isas.keys():
                    check.record_failed(
                        f"ISAs search returned unexpected ISA {self._isa_id}",
                        severity=Severity.High,
                        details=f"Search in area {self._isa_area} to time {latest} returned ISAs {isas.isas.keys()}",
                        query_timestamps=[isas.dss_query.query.request.timestamp],
                    )

            self.end_test_step()

        _search_latest_excl_step()

        def _search_area_only_step():
            self.begin_test_step("Search by area only")

            with self.check(
                "Successful ISAs search", [self._dss_wrapper.participant_id]
            ) as check:
                isas = self._dss_wrapper.search_isas(
                    check,
                    area=self._isa_area,
                )

            with self.check(
                "ISA returned by search", [self._dss_wrapper.participant_id]
            ) as check:
                if self._isa_id not in isas.isas.keys():
                    check.record_failed(
                        f"ISAs search did not return expected ISA {self._isa_id}",
                        severity=Severity.High,
                        details=f"Search in area {self._isa_area} returned ISAs {isas.isas.keys()}",
                        query_timestamps=[isas.dss_query.query.request.timestamp],
                    )

            self.end_test_step()

        _search_area_only_step()

        def _search_invalid_params_step():
            self.begin_test_step("Search with invalid params")

            with self.check(
                "Search request rejected", [self._dss_wrapper.participant_id]
            ) as check:
                _ = self._dss_wrapper.search_isas_expect_response_code(
                    check,
                    expected_error_codes={400},
                    area=[],
                )

            self.end_test_step()

        _search_invalid_params_step()

        def _search_huge_area_step():
            self.begin_test_step("Search by huge area")

            with self.check(
                "Search request rejected", [self._dss_wrapper.participant_id]
            ) as check:
                _ = self._dss_wrapper.search_isas_expect_response_code(
                    check,
                    expected_error_codes={400, 413},
                    area=self._huge_area,
                )

            self.end_test_step()

        _search_huge_area_step()

        def _search_isa_loop_step():
            self.begin_test_step("Search ISA with loop")

            with self.check(
                "Search request rejected", [self._dss_wrapper.participant_id]
            ) as check:
                search_area_loop = self._isa_area.copy()
                search_area_loop.append(search_area_loop[0])
                _ = self._dss_wrapper.search_isas_expect_response_code(
                    check,
                    expected_error_codes={400},
                    area=search_area_loop,
                )

            self.end_test_step()

        _search_isa_loop_step()

        self.end_test_case()

    def _delete_isa_case(self):
        self.begin_test_case("Delete ISA")

        def _delete_wrong_version_step():
            self.begin_test_step("Delete with wrong version")

            with self.check(
                "Delete request rejected", [self._dss_wrapper.participant_id]
            ) as check:
                _ = self._dss_wrapper.del_isa_expect_response_code(
                    check,
                    expected_error_codes={409},
                    isa_id=self._isa_id,
                    isa_version=self._isa_version[1:-1],
                )

            self.end_test_step()

        _delete_wrong_version_step()

        def _delete_empty_version_step():
            self.begin_test_step("Delete with empty version")

            with self.check(
                "Delete request rejected", [self._dss_wrapper.participant_id]
            ) as check:
                _ = self._dss_wrapper.del_isa_expect_response_code(
                    check,
                    expected_error_codes={400},
                    isa_id=self._isa_id,
                    isa_version="",
                )

            self.end_test_step()

        _delete_empty_version_step()

        def _delete_step():
            self.begin_test_step("Delete ISA")

            with self.check("ISA deleted", [self._dss_wrapper.participant_id]) as check:
                _ = self._dss_wrapper.del_isa(
                    check, isa_id=self._isa_id, isa_version=self._isa_version
                )

            self.end_test_step()

        _delete_step()

        def _get_deleted_isa_by_id_step():
            self.begin_test_step("Get deleted ISA by ID")

            with self.check(
                "ISA not found", [self._dss_wrapper.participant_id]
            ) as check:
                _ = self._dss_wrapper.get_isa_expect_response_code(
                    check,
                    expected_error_codes={404},
                    isa_id=self._isa_id,
                )

            self.end_test_step()

        _get_deleted_isa_by_id_step()

        def _search_isa_step():
            self.begin_test_step("Search ISA")

            with self.check(
                "Successful ISAs search", [self._dss_wrapper.participant_id]
            ) as check:
                isas = self._dss_wrapper.search_isas(
                    check,
                    area=self._isa_area,
                )

            with self.check(
                "ISA not returned by search", [self._dss_wrapper.participant_id]
            ) as check:
                if self._isa_id in isas.isas.keys():
                    check.record_failed(
                        f"ISAs search returned deleted ISA {self._isa_id}",
                        severity=Severity.High,
                        details=f"Search in area {self._isa_area} returned ISAs {isas.isas.keys()}",
                        query_timestamps=[isas.dss_query.query.request.timestamp],
                    )

            self.end_test_step()

        _search_isa_step()

        self.end_test_case()

    def cleanup(self):
        self.begin_cleanup()

        self._delete_isa_if_exists()

        self.end_cleanup()
