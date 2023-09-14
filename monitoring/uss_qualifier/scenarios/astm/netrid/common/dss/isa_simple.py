from typing import Optional

import arrow

from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario


class ISASimple(GenericTestScenario):
    """Based on prober/rid/v2/test_isa_simple.py from the legacy prober tool."""

    ISA_TYPE = register_resource_type(348, "ISA")

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
        self._isa_id = id_generator.id_factory.make_id(ISASimple.ISA_TYPE)
        self._isa_version: Optional[str] = None
        self._isa = isa.specification

        now = arrow.utcnow().datetime
        self._isa_start_time = self._isa.shifted_time_start(now)
        self._isa_end_time = self._isa.shifted_time_end(now)
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]

    def run(self):
        self.begin_test_scenario()

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
            self._isa_id, rid_version=self._dss.rid_version, session=self._dss.client
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
                with self.check("Notified subscriber", [subscriber_url]) as check:
                    # TODO: Find a better way to identify a subscriber who couldn't be notified
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

            with self.check("ISA created", [self._dss.participant_id]) as check:
                isa_change = self._dss_wrapper.put_isa(
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
                self._isa_version = isa_change.dss_query.isa.version

            self.end_test_step()

        _create_isa_step()

        self._get_isa_by_id_step()

        self.end_test_case()

    def _update_and_search_isa_case(self):
        self.begin_test_case("Update and search ISA")

        # TODO: Update ISA
        # TODO: Get ISA by ID
        # TODO: Search with invalid params
        # TODO: Search by earliest time (included)
        # TODO: Search by earliest time (excluded)
        # TODO: Search by latest time (included)
        # TODO: Search by latest time (excluded)
        # TODO: Search by area only
        # TODO: Search by huge area

        self.end_test_case()

    def _delete_isa_case(self):
        self.begin_test_case("Delete ISA")

        # TODO: Delete with wrong version
        # TODO: Delete with empty version
        # TODO: Delete ISA
        # TODO: Get ISA by ID
        # TODO: Search ISA
        # TODO: Search ISA with loop

        self.end_test_case()

    def cleanup(self):
        self.begin_cleanup()

        self._delete_isa_if_exists()

        self.end_cleanup()
