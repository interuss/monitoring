from datetime import timedelta

import arrow

from monitoring.monitorlib import schema_validation
from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario


MAX_SKEW = 1e-6  # seconds maximum difference between expected and actual timestamps


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
        self._dss = dss.dss_instance
        self._isa_id = id_generator.id_factory.make_id(ISASimple.ISA_TYPE)
        self._isa = isa.specification

    def run(self):
        self.begin_test_scenario()

        self._setup_case()
        self._create_and_check_isa_case()
        self._update_and_search_isa_case()
        self._delete_isa_case()

        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")

        self._ensure_clean_workspace_step()

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

    def _ensure_clean_workspace_step(self):
        self.begin_test_step("Ensure clean workspace")

        self._delete_isa_if_exists()

        self.end_test_step()

    def _create_and_check_isa_case(self):
        self.begin_test_case("Create and check ISA")

        self._create_isa_step()

        # TODO: Get ISA by ID

        self.end_test_case()

    def _create_isa_step(self):
        self.begin_test_step("Create ISA")

        start_time = arrow.utcnow().datetime + timedelta(seconds=1)
        end_time = start_time + timedelta(minutes=60)
        area = self._isa.footprint.to_vertices()
        isa_change = mutate.put_isa(
            area_vertices=area,
            start_time=start_time,
            end_time=end_time,
            uss_base_url=self._isa.base_url,
            isa_id=self._isa_id,
            rid_version=self._dss.rid_version,
            utm_client=self._dss.client,
            isa_version=None,
            alt_lo=self._isa.altitude_min,
            alt_hi=self._isa.altitude_max,
        )
        self.record_query(isa_change.dss_query.query)
        for notification_query in isa_change.notifications.values():
            self.record_query(notification_query.query)
        t_dss = isa_change.dss_query.query.request.timestamp

        with self.check("ISA created", [self._dss.participant_id]) as check:
            if isa_change.dss_query.status_code == 200:
                check.record_passed()
            elif isa_change.dss_query.status_code == 201:
                check.record_failed(
                    f"PUT ISA returned technically-incorrect 201",
                    Severity.Low,
                    "DSS should return 200 from PUT ISA, but instead returned the reasonable-but-technically-incorrect code 201",
                    query_timestamps=[t_dss],
                )
            else:
                check.record_failed(
                    f"PUT ISA returned {isa_change.dss_query.status_code}",
                    Severity.High,
                    f"DSS should return 200 from PUT ISA, but instead returned {isa_change.dss_query.status_code}",
                    query_timestamps=[t_dss],
                )

        with self.check("ISA ID matches", [self._dss.participant_id]) as check:
            if isa_change.dss_query.isa.id != self._isa_id:
                check.record_failed(
                    f"PUT ISA returned ISA with incorrect ID",
                    Severity.High,
                    f"DSS should have recorded and returned the ISA ID {self._isa_id} as requested in the path, but response body instead specified {isa_change.dss_query.isa.id}",
                    query_timestamps=[t_dss],
                )
        with self.check("ISA URL matches", [self._dss.participant_id]) as check:
            expected_flights_url = self._dss.rid_version.flights_url_of(
                self._isa.base_url
            )
            actual_flights_url = isa_change.dss_query.isa.flights_url
            if actual_flights_url != expected_flights_url:
                check.record_failed(
                    f"PUT ISA returned ISA with incorrect URL",
                    Severity.High,
                    f"DSS should have returned an ISA with a flights URL of {expected_flights_url}, but instead the ISA returned had a flights URL of {actual_flights_url}",
                    query_timestamps=[t_dss],
                )
        with self.check("ISA start time matches", [self._dss.participant_id]) as check:
            if (
                abs((isa_change.dss_query.isa.time_start - start_time).total_seconds())
                > MAX_SKEW
            ):
                check.record_failed(
                    "PUT ISA returned ISA with incorrect start time",
                    Severity.High,
                    f"DSS should have returned an ISA with a start time of {start_time}, but instead the ISA returned had a start time of {isa_change.dss_query.isa.time_start}",
                    query_timestamps=[t_dss],
                )
        with self.check("ISA end time matches", [self._dss.participant_id]) as check:
            if (
                abs((isa_change.dss_query.isa.time_end - end_time).total_seconds())
                > MAX_SKEW
            ):
                check.record_failed(
                    "PUT ISA returned ISA with incorrect end time",
                    Severity.High,
                    f"DSS should have returned an ISA with an end time of {end_time}, but instead the ISA returned had an end time of {isa_change.dss_query.isa.time_end}",
                    query_timestamps=[t_dss],
                )
        with self.check("ISA version format", [self._dss.participant_id]) as check:
            if not all(
                c not in "\0\t\r\n#%/:?@[\]" for c in isa_change.dss_query.isa.version
            ):
                check.record_failed(
                    "PUT ISA returned ISA with invalid version format",
                    Severity.High,
                    f"DSS returned an ISA with a version that is not URL-safe: {isa_change.dss_query.isa.version}",
                    query_timestamps=[t_dss],
                )

        with self.check("ISA response format", [self._dss.participant_id]) as check:
            errors = schema_validation.validate(
                self._dss.rid_version.openapi_path,
                self._dss.rid_version.openapi_put_isa_response_path,
                isa_change.dss_query.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                check.record_failed(
                    "PUT ISA response format was invalid",
                    Severity.Medium,
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    query_timestamps=[t_dss],
                )

        # TODO: Validate subscriber notifications

        self.end_test_step()

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
