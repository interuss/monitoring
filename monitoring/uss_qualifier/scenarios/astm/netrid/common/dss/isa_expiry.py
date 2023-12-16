import datetime
import time
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
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class ISAExpiry(GenericTestScenario):
    """Based on test_isa_expiry.py from the legacy prober tool."""

    ISA_TYPE = register_resource_type(369, "ISA")

    _create_isa_path: str

    _write_scope: str

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
        self._isa_id = id_generator.id_factory.make_id(ISAExpiry.ISA_TYPE)
        self._isa_version: Optional[str] = None
        self._isa = isa.specification

        now = arrow.utcnow().datetime
        self._isa_start_time = self._isa.shifted_time_start(now)
        self._isa_end_time = self._isa.shifted_time_end(now)
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self._setup_case()

        self.begin_test_case("ISA Expiry")
        self.begin_test_step("ISA Expiry")

        self._check_expiry_behaviors()

        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()

    def _check_expiry_behaviors(self):
        """
        Once an ISA is expired, it may still be queried directly using its ID,
        but it should not appear in searches anymore.
        """

        start_time = datetime.datetime.utcnow()
        end_time = start_time + datetime.timedelta(seconds=5)

        # Create a short-lived ISA of a few seconds
        with self.check("Create short-lived ISA", [self._dss.participant_id]) as check:
            created_isa = self._dss_wrapper.put_isa_expect_response_code(
                check=check,
                expected_error_codes={200},
                area_vertices=self._isa_area,
                alt_lo=self._isa.altitude_min,
                alt_hi=self._isa.altitude_max,
                start_time=start_time,
                end_time=end_time,
                uss_base_url=self._isa.base_url,
                isa_id=self._isa_id,
                isa_version=None,
            )

        # Wait for it to expire
        time.sleep(5)

        # Search for ISAs: we should not find the expired one
        with self.check(
            "Expired ISAs are not part of search results", [self._dss.participant_id]
        ) as check:
            isas = self._dss_wrapper.search_isas_expect_response_code(
                main_check=check,
                expected_error_codes={200},
                area=self._isa_area,
            )
            if self._isa_id in isas.isas.keys():
                check.record_failed(
                    summary=f"Expired ISA {self._isa_id} found in search results",
                    severity=Severity.Medium,
                    details=f"Searched for area {self._isa_area} with unspecified end and start time.",
                    query_timestamps=[
                        created_isa.dss_query.query.request.timestamp,
                        isas.query.request.timestamp,
                    ],
                )

        with self.check(
            "An expired ISA can be queried by its ID", [self._dss.participant_id]
        ) as check:
            self._dss_wrapper.get_isa(check, self._isa_id)

    def _setup_case(self):
        self.begin_test_case("Setup")

        def _ensure_clean_workspace_step():
            self.begin_test_step("Ensure clean workspace")

            self._delete_isa_if_exists()

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
            ignore_base_url=self._isa.base_url,
        )

    def cleanup(self):
        self.begin_cleanup()

        self._delete_isa_if_exists()

        self.end_cleanup()
